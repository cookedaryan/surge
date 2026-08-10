package com.power.surge.dto.report;

import com.power.surge.domain.JobStatus;

import java.util.UUID;

public record ScenarioSummaryItem(
        String scenarioName,
        UUID jobId,
        JobStatus status,
        Double totalNetworkLengthMeters,
        Integer totalPoles,
        Double totalEstimatedCost,
        Double totalElectricalLossesKw,
        Double landRowCompensationCost,
        Double capexDeltaPct,
        Double lossesDeltaPct
) {
}
