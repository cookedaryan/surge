package com.power.surge.service;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.LinkedHashMap;
import java.util.Map;

public record LandOutcome(
        Integer parcelCount,
        Integer ownerInteractionCount,
        String ownerInteractionBasis,
        Integer unknownOwnerCount,
        String landCostBasis,
        Boolean isFeasible,
        Map<String, LandParcelDecision> parcelDecisions
) {

    private static final ObjectMapper MAPPER = new ObjectMapper();

    public record LandParcelDecision(
            String parcelId,
            String ownerId,
            String availabilityStatus,
            String selectedMode,
            BigDecimal selectedPresentValue,
            String costBasis,
            String priceDate,
            Double affectedAreaM2
    ) {}

    public static LandOutcome fromResultSummaryJson(String resultSummaryJson) {
        if (resultSummaryJson == null) return null;
        try {
            JsonNode root = MAPPER.readTree(resultSummaryJson);
            JsonNode recommendation = root.get("recommendation");
            if (recommendation == null || !recommendation.hasNonNull("recommended_scenario_id")) return null;
            String recommendedId = recommendation.get("recommended_scenario_id").asText();

            JsonNode candidates = root.get("candidates");
            if (candidates == null || !candidates.isArray()) return null;

            JsonNode targetCandidate = null;
            for (JsonNode cand : candidates) {
                if (cand.hasNonNull("scenario_id") && recommendedId.equals(cand.get("scenario_id").asText())) {
                    targetCandidate = cand;
                    break;
                }
            }
            if (targetCandidate == null || !targetCandidate.hasNonNull("land")) return null;
            JsonNode land = targetCandidate.get("land");

            Map<String, LandParcelDecision> decisions = new LinkedHashMap<>();
            JsonNode parcelDecisions = land.get("parcel_decisions");
            if (parcelDecisions != null && parcelDecisions.isArray()) {
                for (JsonNode pd : parcelDecisions) {
                    if (!pd.hasNonNull("parcel_id")) continue;
                    decisions.put(pd.get("parcel_id").asText(), new LandParcelDecision(
                            pd.get("parcel_id").asText(),
                            pd.hasNonNull("owner_id") ? pd.get("owner_id").asText() : null,
                            pd.hasNonNull("availability_status") ? pd.get("availability_status").asText() : null,
                            pd.hasNonNull("selected_mode") ? pd.get("selected_mode").asText() : null,
                            pd.hasNonNull("selected_present_value") ? new BigDecimal(pd.get("selected_present_value").asText()).setScale(2, RoundingMode.HALF_UP) : null,
                            pd.hasNonNull("cost_basis") ? pd.get("cost_basis").asText() : null,
                            pd.hasNonNull("price_date") ? pd.get("price_date").asText() : null,
                            pd.hasNonNull("affected_area_m2") ? pd.get("affected_area_m2").asDouble() : null
                    ));
                }
            }

            return new LandOutcome(
                    land.hasNonNull("parcel_count") ? land.get("parcel_count").asInt() : null,
                    land.hasNonNull("owner_interaction_count") ? land.get("owner_interaction_count").asInt() : null,
                    land.hasNonNull("owner_interaction_basis") ? land.get("owner_interaction_basis").asText() : null,
                    land.hasNonNull("unknown_owner_count") ? land.get("unknown_owner_count").asInt() : null,
                    land.hasNonNull("land_cost_basis") ? land.get("land_cost_basis").asText() : null,
                    land.hasNonNull("is_feasible") ? land.get("is_feasible").asBoolean() : null,
                    decisions
            );
        } catch (JsonProcessingException e) {
            return null;
        }
    }
}
