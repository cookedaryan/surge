package com.power.surge.repository;

import com.power.surge.domain.CostCatalogue;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.UUID;

@Repository
public interface CostCatalogueRepository extends JpaRepository<CostCatalogue, UUID> {

    /**
     * The enabled catalogues, newest price basis first, with their items already loaded.
     *
     * <p>Fetched eagerly because the caller always needs every rate: a catalogue is only useful as a
     * complete set, and loading the items lazily one query at a time would be a select for every
     * conductor on a page that wants them all.
     */
    @Query("""
            select distinct c from CostCatalogue c
            left join fetch c.conductorItems
            left join fetch c.poleItems
            where c.enabled = true
            order by c.priceBasisDate desc
            """)
    List<CostCatalogue> findEnabledWithItems();
}
