package com.power.surge.service;

import com.power.surge.domain.CableDataProvenance;
import com.power.surge.domain.CableType;
import com.power.surge.repository.CableTypeRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * Supplies the conductors the optimiser is allowed to size against.
 *
 * <p>Without a catalogue the Python compatibility layer invents one cable, back-deriving its
 * ampacity from the feeder capacity typed into the UI and using placeholder impedances. That makes
 * per-segment cable sizing meaningless — there is nothing to select — and quietly puts every
 * electrical figure on a fictional conductor.
 */
@Service
@Transactional(readOnly = true)
public class CableCatalogueService {

    private static final Logger log = LoggerFactory.getLogger(CableCatalogueService.class);

    private final CableTypeRepository cableTypeRepository;

    public CableCatalogueService(CableTypeRepository cableTypeRepository) {
        this.cableTypeRepository = cableTypeRepository;
    }

    /**
     * Builds the {@code cable_config} payload for a run at this voltage.
     *
     * <p>Returns null when the catalogue holds nothing usable, which leaves the engine on its
     * compatibility cable exactly as before. That is deliberate: a run on a placeholder conductor
     * is worth more than no run at all, and the report says which conductor was used either way.
     *
     * <p>Voltage tolerance comes from the run's own maximum voltage drop, matching what the
     * compatibility path did, so switching to a real catalogue does not silently move the limits
     * the load flow is judged against.
     */
    public Map<String, Object> buildCableConfig(BigDecimal nominalVoltageKv, BigDecimal maxVoltageDropPct) {
        List<CableType> available = cableTypeRepository
                .findAllByNominalVoltageKvAndEnabledTrueOrderByMaxCurrentAAsc(nominalVoltageKv);

        if (available.isEmpty()) {
            log.warn("No cable types configured for {} kV; the optimiser will fall back to its "
                    + "synthesised compatibility conductor and its placeholder impedances.", nominalVoltageKv);
            return null;
        }

        double tolerance = (maxVoltageDropPct != null ? maxVoltageDropPct.doubleValue() : 5.0) / 100.0;

        List<Map<String, Object>> cableTypes = new ArrayList<>();
        for (CableType cable : available) {
            Map<String, Object> entry = new LinkedHashMap<>();
            entry.put("cable_type_id", cable.getCableTypeId());
            entry.put("resistance_ohm_per_km", cable.getResistanceOhmPerKm().doubleValue());
            entry.put("reactance_ohm_per_km", cable.getReactanceOhmPerKm().doubleValue());
            entry.put("capacitance_nf_per_km", cable.getCapacitanceNfPerKm().doubleValue());
            entry.put("max_current_a", cable.getMaxCurrentA().doubleValue());
            entry.put("parallel_count", cable.getParallelCount());
            entry.put("derating_factor", cable.getDeratingFactor().doubleValue());
            cableTypes.add(entry);
        }

        Map<String, Object> config = new LinkedHashMap<>();
        config.put("nominal_voltage_kv", nominalVoltageKv.doubleValue());
        config.put("min_voltage_pu", Math.max(0.001, 1.0 - tolerance));
        config.put("max_voltage_pu", 1.0 + tolerance);
        config.put("cable_types", cableTypes);
        // The largest conductor is the safe default: sizing steps down from something that can
        // certainly carry the load, rather than starting below it and having to fail.
        config.put("default_cable_type_id", available.get(available.size() - 1).getCableTypeId());
        return config;
    }

    /**
     * Describes how far the catalogue behind a run can be trusted.
     *
     * <p>Reported alongside the results because unverified conductor parameters produce figures
     * that look exactly as authoritative as verified ones.
     */
    public String describeProvenance(BigDecimal nominalVoltageKv) {
        List<CableType> available = cableTypeRepository
                .findAllByNominalVoltageKvAndEnabledTrueOrderByMaxCurrentAAsc(nominalVoltageKv);
        if (available.isEmpty()) {
            return "No catalogue configured — results use the engine's synthesised placeholder conductor.";
        }
        long unverified = available.stream()
                .filter(c -> c.getDataProvenance() != CableDataProvenance.VERIFIED)
                .count();
        if (unverified == 0) {
            return "All " + available.size() + " conductors verified against supplier data.";
        }
        return unverified + " of " + available.size() + " conductors carry unverified parameters; "
                + "electrical results are indicative until they are checked against supplier datasheets.";
    }
}
