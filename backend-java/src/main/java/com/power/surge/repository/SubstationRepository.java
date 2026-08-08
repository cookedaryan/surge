package com.power.surge.repository;

import com.power.surge.domain.Substation;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;
import java.util.UUID;

public interface SubstationRepository extends JpaRepository<Substation, UUID> {

    List<Substation> findAllByProjectIdOrderByExternalIdAsc(UUID projectId);
}
