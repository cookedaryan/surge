package com.power.surge.repository;

import com.power.surge.domain.CableType;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.math.BigDecimal;
import java.util.List;
import java.util.UUID;

@Repository
public interface CableTypeRepository extends JpaRepository<CableType, UUID> {

    /**
     * The conductors available at a given system voltage, smallest first.
     *
     * <p>Ordered by ampacity so the sizing engine sees the cheapest adequate conductor before the
     * larger ones, and so a report reads in a sensible progression.
     */
    List<CableType> findAllByNominalVoltageKvAndEnabledTrueOrderByMaxCurrentAAsc(BigDecimal nominalVoltageKv);

    List<CableType> findAllByEnabledTrueOrderByMaxCurrentAAsc();
}
