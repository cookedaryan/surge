class CandidateElectricalEvaluationError(Exception):
    """Execution error evaluating an individual candidate network.

    This indicates a localized failure such as pandapower crashing on a single
    unusual topology, rather than a shared configuration error.
    """

    pass
