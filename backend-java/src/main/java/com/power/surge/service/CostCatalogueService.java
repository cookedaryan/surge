package com.power.surge.service;

import com.power.surge.domain.CableDataProvenance;
import com.power.surge.domain.CableType;
import com.power.surge.domain.ConductorCostItem;
import com.power.surge.domain.CostCatalogue;
import com.power.surge.domain.PoleCostItem;
import com.power.surge.repository.CableTypeRepository;
import com.power.surge.repository.CostCatalogueRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.TreeSet;
import java.util.stream.Collectors;

/**
 * Supplies the rates a run is costed against.
 *
 * <p>Python computes conductor CAPEX, pole CAPEX, land cost, loss valuation and a lifecycle total —
 * but only for a request carrying a {@code costing_config}. Java never sent one, so every candidate
 * the application has received came back with {@code cost: null}, while the UI displayed money
 * derived from {@code route length × 80}: a constant with no basis and no currency.
 */
@Service
@Transactional(readOnly = true)
public class CostCatalogueService {

    private static final Logger log = LoggerFactory.getLogger(CostCatalogueService.class);

    /** Python validates these four exactly, lowercased. */
    private static final Set<String> REQUIRED_POLE_TYPES =
            Set.of("terminal", "angle", "intermediate", "junction");

    private final CostCatalogueRepository costCatalogueRepository;
    private final CableTypeRepository cableTypeRepository;

    public CostCatalogueService(CostCatalogueRepository costCatalogueRepository,
                                CableTypeRepository cableTypeRepository) {
        this.costCatalogueRepository = costCatalogueRepository;
        this.cableTypeRepository = cableTypeRepository;
    }

    /**
     * Builds the {@code costing_config} payload, or null when there is nothing usable to send.
     *
     * <p>Null means the run proceeds uncosted, exactly as every run has until now. That is the right
     * failure: a route optimised without a price is still a route, whereas a route priced against
     * invented rates is a number somebody will act on.
     */
    public Map<String, Object> buildCostingConfig() {
        Optional<CostCatalogue> selected = activeCatalogue();
        if (selected.isEmpty()) {
            log.warn("No enabled cost catalogue; the run will proceed uncosted and every candidate "
                    + "will report cost: null.");
            return null;
        }

        CostCatalogue catalogue = selected.get();
        if (catalogue.getConductorItems().isEmpty() || catalogue.getPoleItems().isEmpty()) {
            log.warn("Cost catalogue {} has no {} rates; sending it would price part of the network "
                            + "and void the total, so the run proceeds uncosted instead.",
                    catalogue.getCatalogueId(),
                    catalogue.getConductorItems().isEmpty() ? "conductor" : "pole");
            return null;
        }

        List<Map<String, Object>> conductorItems = new ArrayList<>();
        for (ConductorCostItem item : catalogue.getConductorItems()) {
            Map<String, Object> entry = new LinkedHashMap<>();
            entry.put("cable_type_id", item.getCableTypeId());
            entry.put("installed_cost_per_km_per_parallel_circuit",
                    item.getInstalledCostPerKmPerCircuit().doubleValue());
            conductorItems.add(entry);
        }

        List<Map<String, Object>> poleItems = new ArrayList<>();
        for (PoleCostItem item : catalogue.getPoleItems()) {
            Map<String, Object> entry = new LinkedHashMap<>();
            entry.put("pole_type", item.getPoleType());
            entry.put("installed_cost_each", item.getInstalledCostEach().doubleValue());
            poleItems.add(entry);
        }

        Map<String, Object> landPolicy = new LinkedHashMap<>();
        landPolicy.put("fixed_cost_per_affected_parcel", catalogue.getLandFixedCostPerParcel().doubleValue());
        landPolicy.put("variable_basis", catalogue.getLandVariableBasis());
        landPolicy.put("variable_rate", catalogue.getLandVariableRate().doubleValue());

        Map<String, Object> catalogueNode = new LinkedHashMap<>();
        catalogueNode.put("catalogue_id", catalogue.getCatalogueId());
        catalogueNode.put("version", catalogue.getVersion());
        catalogueNode.put("currency", catalogue.getCurrency());
        catalogueNode.put("price_basis_date", catalogue.getPriceBasisDate().format(DateTimeFormatter.ISO_DATE));
        catalogueNode.put("conductor_items", conductorItems);
        catalogueNode.put("pole_items", poleItems);
        catalogueNode.put("land_policy", landPolicy);

        Map<String, Object> lifecycle = new LinkedHashMap<>();
        lifecycle.put("currency", catalogue.getCurrency());
        lifecycle.put("energy_price_basis_date",
                catalogue.getEnergyPriceBasisDate().format(DateTimeFormatter.ISO_DATE));
        lifecycle.put("analysis_period_years", catalogue.getAnalysisPeriodYears());
        lifecycle.put("discount_rate", catalogue.getDiscountRate().doubleValue());
        lifecycle.put("annual_operating_hours", catalogue.getAnnualOperatingHours());
        lifecycle.put("loss_load_factor", catalogue.getLossLoadFactor().doubleValue());
        lifecycle.put("energy_price_per_mwh", catalogue.getEnergyPricePerMwh().doubleValue());

        Map<String, Object> config = new LinkedHashMap<>();
        config.put("catalogue", catalogueNode);
        config.put("lifecycle", lifecycle);
        return config;
    }

    /** The currency every rate in the active catalogue is quoted in, or empty when uncosted. */
    public Optional<String> activeCurrency() {
        return activeCatalogue().map(CostCatalogue::getCurrency);
    }

    /**
     * Conductors the cable catalogue offers but the cost catalogue does not price.
     *
     * <p>Worth naming separately from a missing catalogue: the run picks the conductor, so a single
     * gap here produces {@code CABLE_COST_NOT_FOUND} and no total at all. A catalogue can look
     * complete and still buy nothing.
     */
    public Set<String> conductorsWithoutRates() {
        Optional<CostCatalogue> selected = activeCatalogue();
        if (selected.isEmpty()) {
            return Set.of();
        }
        Set<String> priced = selected.get().getConductorItems().stream()
                .map(ConductorCostItem::getCableTypeId)
                .collect(Collectors.toSet());
        return cableTypeRepository.findAllByEnabledTrueOrderByMaxCurrentAAsc().stream()
                .map(CableType::getCableTypeId)
                .filter(id -> !priced.contains(id))
                .collect(Collectors.toCollection(TreeSet::new));
    }

    /**
     * Describes how far the money behind a run can be trusted.
     *
     * <p>Reported wherever a cost is shown, because a rate nobody has obtained a quotation for
     * produces a total that looks exactly as authoritative as a tendered one.
     */
    public String describeProvenance() {
        Optional<CostCatalogue> selected = activeCatalogue();
        if (selected.isEmpty()) {
            return "No cost catalogue configured — this run carries no costs.";
        }

        CostCatalogue catalogue = selected.get();
        StringBuilder description = new StringBuilder();
        description.append("Costed against ")
                .append(catalogue.getCatalogueId())
                .append(" v")
                .append(catalogue.getVersion())
                .append(" in ")
                .append(catalogue.getCurrency())
                .append(", priced as at ")
                .append(catalogue.getPriceBasisDate());

        long unverifiedItems = catalogue.getConductorItems().stream()
                .filter(i -> i.getDataProvenance() != CableDataProvenance.VERIFIED)
                .count()
                + catalogue.getPoleItems().stream()
                .filter(i -> i.getDataProvenance() != CableDataProvenance.VERIFIED)
                .count();
        int totalItems = catalogue.getConductorItems().size() + catalogue.getPoleItems().size();

        if (unverifiedItems > 0) {
            description.append(". ")
                    .append(unverifiedItems)
                    .append(" of ")
                    .append(totalItems)
                    .append(" rates are unverified; these figures are for comparing scenarios, ")
                    .append("not for committing money.");
        } else {
            description.append(". All ").append(totalItems).append(" rates verified.");
        }

        Set<String> unpriced = conductorsWithoutRates();
        if (!unpriced.isEmpty()) {
            description.append(" No rate for ")
                    .append(String.join(", ", unpriced))
                    .append(" — a run selecting one of those reports no total.");
        }

        Set<String> missingPoleTypes = new TreeSet<>(REQUIRED_POLE_TYPES);
        catalogue.getPoleItems().forEach(i -> missingPoleTypes.remove(i.getPoleType()));
        if (!missingPoleTypes.isEmpty()) {
            description.append(" No rate for ")
                    .append(String.join(", ", missingPoleTypes))
                    .append(" poles.");
        }

        return description.toString();
    }

    /**
     * The catalogue a run should use: enabled, with the most recent price basis.
     *
     * <p>Most recent rather than a configured default, so adding this year's rates takes effect
     * without an extra switch to remember to flip.
     */
    private Optional<CostCatalogue> activeCatalogue() {
        List<CostCatalogue> enabled = costCatalogueRepository.findEnabledWithItems();
        return enabled.isEmpty() ? Optional.empty() : Optional.of(enabled.get(0));
    }
}
