import graph_objects as go
import graph_lattice_functions as gf
from progiter import ProgIter
import multiprocessing as mp


def single(
    size,
    config,
    dec,
    pE=0,
    pX=0,
    pZ=0,
    graph=None,
    worker=0,
    iter=0,
    seed=None,
    **kwargs
):
    """
    Runs the peeling decoder for one iteration
    """
    # Initialize lattice
    if graph is None:
        if config.type == "toric":
            decoder = dec.toric(graph, plot_config=config.plot, **config.decoder)
            graph = gf.init_toric_graph(size, decoder, config.plot_load, config.plot)
        elif config.type == "planar":
            decoder = dec.planar(graph, plot_config=config.plot, **config.decoder)
            graph = gf.init_planar_graph(size, decoder, config.plot_load, config.plot)
        decoder.graph = graph


    # Initialize errors
    if seed is None and config.seed is None:
        gf.init_random_seed(worker=worker, iteration=iter)
    elif seed is None:
        gf.apply_random_seed(config.seed)
    elif config.seed is None:
        gf.apply_random_seed(seed)

    if pE != 0:
        gf.init_erasure(graph, pE, **config.file)

    gf.init_pauli(graph, pX, pZ, **config.file)         # initialize errors
    gf.measure_stab(graph)                              # Measure stabiliziers

    # Peeling decoder
    graph.decoder.decode()

    # Measure logical operator
    logical_error, correct = gf.logical_error(graph)
    graph.reset()

    return correct


def multiple(
    size,
    config,
    dec,
    iters,
    pE=0,
    pX=0,
    pZ=0,
    qres=None,
    worker=0,
    seeds=None,
    **kwargs
):
    """
    Runs the peeling decoder for a number of iterations. The graph is reused for speedup.
    """

    if seeds is None:
        seeds = [gf.init_random_seed(worker=worker, iteration=iter) for iter in range(iters)]

    if config.type == "toric":
        decoder = dec.toric(None, plot_config=config.plot, **config.decoder)
        graph = gf.init_toric_graph(size, decoder, config.plot_load, config.plot)
    elif config.type == "planar":
        decoder = dec.planar(None, plot_config=config.plot, **config.decoder)
        graph = gf.init_planar_graph(size, decoder, config.plot_load, config.plot)
    decoder.graph = graph

    result = [
        single(size, config, dec, pE, pX, pZ, graph, worker, i, seed)
        for i, seed in zip(ProgIter(range(iters)), seeds)
    ]

    N_succes = sum(result)
    if qres is not None:
        qres.put(N_succes)
    else:
        return N_succes


def multiprocess(size, config, dec, iters, pE=0, pX=0, pZ=0, seeds=None, processes=None, **kwargs):
    """
    Runs the peeling decoder for a number of iterations, split over a number of processes
    """

    if processes is None:
        processes = mp.cpu_count()

    # Calculate iterations for ieach child process
    process_iters = iters // processes
    rest_iters = iters - process_iters * (processes - 1)

    # Generate seeds for simulations
    if seeds is None:
        num_seeds = [process_iters for _ in range(processes - 1)] + [rest_iters]
        seed_lists = [[gf.init_random_seed(worker=worker, iteration=iter) for iter in range(iters)] for worker, iters in enumerate(num_seeds)]
    else:
        seed_lists = [seeds[int(i*process_iters):int((i+1)*process_iters)] for i in range(processes - 1)] + [seeds[int((processes-1)*process_iters):]]

    if dec is None:
        import unionfind as dec

    # Initiate processes
    qres = mp.Queue()
    workers = []
    for i in range(processes - 1):
        workers.append(
            mp.Process(
                target=multiple,
                args=(size, config, dec, process_iters, pE, pX, pZ, qres, i, seed_lists[i]),
            )
        )
    workers.append(
        mp.Process(
            target=multiple,
            args=(
                size,
                config,
                dec,
                rest_iters,
                pE,
                pX,
                pZ,
                qres,
                processes - 1,
                seed_lists[processes - 1],
            ),
        )
    )
    print("Starting", processes, "workers.")

    # Start and join processes
    for worker in workers:
        worker.start()

    N_succes = sum([qres.get() for worker in workers])

    for worker in workers:
        worker.join()

    return N_succes


class decoder_config(object):
    def __init__(self, path="./unionfind.ini"):

        self.plot_load = 0
        self.seed = None
        self.type = "planar"

        self.decoder = {
            "random_order"  : 0,
            "random_traverse": 0,
            "print_steps"   : 0,
            "plot_find"     : 0,
            "plot_growth"   : 0,
            "plot_peel"     : 0,

            # Evengrow
            "plot_nodes": 1,
            "print_nodetree": 1,
        }

        self.file = {
            "savefile": 0,
            "erasure_file": None,
            "pauli_file": None,
        }

        self.plot = {
            "plot_size"     : 6,
            "line_width"    : 1.5,
            "plotstep_click": 1,
        }


if __name__ == "__main__":

    import unionfind as decoder

    size = 8

    pX = 0.09
    pZ = 0.0
    pE = 0.
    iters = 50000

    # output = single(size, decoder_config(), decoder, pE, pX, pZ)
    # output = multiple(size, decoder_config(), decoder, iters, pE, pX, pZ)
    output = multiprocess(size, decoder_config(), decoder, iters, pE, pX, pZ)

    print(output, output/iters)