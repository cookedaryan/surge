"""WP5-1 — Monotone-transform MST invariance regression test.

Pins the audited F2 finding: the transformation ``w' = w * (1 + α·w/w_max)``
preserves the MST edge set because it is a strictly monotone function of ``w``
for fixed ``w_max > 0``.

For 100 seeded random graphs and a declared set of ``alpha`` values, the MST
edge set after the transform must equal the original.
"""

import math
import random

import networkx as nx
import pytest

from app.optimisation.scenarios import _apply_long_edge_penalty

# Declared alpha values to test.  alpha=0 is a trivial identity; the rest
# exercise the non-linear amplification at increasing strength.
ALPHA_VALUES: list[float] = [0.0, 0.5, 1.0, 2.0, 5.0, 10.0]

# Number of seeded random graphs.
NUM_GRAPHS: int = 100

# Graph parameters for gnp_random_graph.
NUM_NODES: int = 15
EDGE_PROBABILITY: float = 0.4
MASTER_SEED: int = 20260917


def _build_weighted_graph(seed: int) -> nx.Graph:
    """Create a random connected graph with positive edge weights."""
    rng = random.Random(seed)
    # Use gnp_random_graph with a fixed seed for reproducibility
    g = nx.gnp_random_graph(NUM_NODES, EDGE_PROBABILITY, seed=seed)

    # Ensure the graph is connected by adding edges for disconnected components
    components = list(nx.connected_components(g))
    for i in range(1, len(components)):
        # Connect each component to the first
        u = next(iter(components[0]))
        v = next(iter(components[i]))
        g.add_edge(u, v)

    # Assign random positive weights
    for u, v in g.edges():
        g[u][v]["weight"] = rng.uniform(0.1, 100.0)

    return g


def _mst_edge_set(graph: nx.Graph) -> frozenset[tuple[int, int]]:
    """Extract the MST edge set as a frozenset of sorted-node pairs."""
    mst_edges = nx.minimum_spanning_edges(graph, data=False)
    return frozenset(tuple(sorted(e)) for e in mst_edges)


def _generate_seeds() -> list[int]:
    """Generate deterministic per-graph seeds from the master seed."""
    rng = random.Random(MASTER_SEED)
    return [rng.randint(0, 2**31 - 1) for _ in range(NUM_GRAPHS)]


GRAPH_SEEDS = _generate_seeds()


class TestMSTInvariance:
    """The monotone edge-weight transform must not change the MST edge set."""

    @pytest.mark.parametrize("alpha", ALPHA_VALUES)
    @pytest.mark.parametrize(
        "graph_seed", GRAPH_SEEDS, ids=[f"G{i}" for i in range(NUM_GRAPHS)]
    )
    def test_mst_edge_set_unchanged(self, graph_seed: int, alpha: float) -> None:
        graph = _build_weighted_graph(graph_seed)
        original_mst = _mst_edge_set(graph)

        penalised = _apply_long_edge_penalty(graph, alpha=alpha)

        # The original graph must not have been mutated
        for u, v, data in graph.edges(data=True):
            assert "weight" in data, f"Edge ({u},{v}) lost its weight"

        penalised_mst = _mst_edge_set(penalised)

        assert original_mst == penalised_mst, (
            f"MST changed with alpha={alpha}, seed={graph_seed}. "
            f"Original edges: {sorted(original_mst)}, "
            f"Penalised edges: {sorted(penalised_mst)}"
        )

    @pytest.mark.parametrize("alpha", ALPHA_VALUES)
    def test_transform_is_strictly_monotone(self, alpha: float) -> None:
        """Verify the mathematical invariant: the transform preserves edge
        weight ordering for any w_max > 0.

        For two edges with weights w1 < w2, the transformed weights w1' < w2'
        must preserve the strict ordering.
        """
        if alpha == 0.0:
            return  # Identity transform; trivially monotone

        for w_max in [1.0, 10.0, 100.0, 1000.0]:
            for w1 in [0.1, 1.0, 5.0, 50.0]:
                for w2_offset in [0.01, 0.1, 1.0, 10.0]:
                    w2 = w1 + w2_offset
                    if w2 > w_max:
                        continue  # Skip invalid pairs

                    w1_prime = w1 * (1.0 + alpha * w1 / w_max)
                    w2_prime = w2 * (1.0 + alpha * w2 / w_max)

                    assert w1_prime < w2_prime, (
                        f"Monotonicity violated: w1={w1} -> {w1_prime}, "
                        f"w2={w2} -> {w2_prime}, alpha={alpha}, w_max={w_max}"
                    )

    def test_alpha_zero_returns_same_graph(self) -> None:
        """Alpha=0 returns the input graph object unchanged (identity)."""
        graph = _build_weighted_graph(GRAPH_SEEDS[0])
        result = _apply_long_edge_penalty(graph, alpha=0.0)
        # _apply_long_edge_penalty returns graph (not a copy) when alpha=0
        assert result is graph

    def test_original_graph_not_mutated(self) -> None:
        """The penalty function must not mutate the original graph."""
        graph = _build_weighted_graph(GRAPH_SEEDS[0])
        original_weights = {
            (u, v): data["weight"] for u, v, data in graph.edges(data=True)
        }
        _apply_long_edge_penalty(graph, alpha=2.0)

        for (u, v), original_w in original_weights.items():
            assert graph[u][v]["weight"] == original_w, (
                f"Edge ({u},{v}) weight was mutated from {original_w} "
                f"to {graph[u][v]['weight']}"
            )

    def test_non_finite_weights_are_preserved(self) -> None:
        """Edges with non-finite weights (inf) must be left unchanged."""
        graph = _build_weighted_graph(GRAPH_SEEDS[0])
        # Set one edge to infinity
        u, v = next(iter(graph.edges()))
        graph[u][v]["weight"] = float("inf")

        penalised = _apply_long_edge_penalty(graph, alpha=2.0)
        assert math.isinf(penalised[u][v]["weight"]), (
            "Non-finite weight should be preserved"
        )
