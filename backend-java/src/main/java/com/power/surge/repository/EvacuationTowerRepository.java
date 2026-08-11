package com.power.surge.repository;

import com.power.surge.domain.EvacuationTower;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;
import java.util.UUID;

public interface EvacuationTowerRepository extends JpaRepository<EvacuationTower, UUID> {

    List<EvacuationTower> findAllByProjectIdOrderByExternalIdAsc(UUID projectId);

    long countByProjectId(UUID projectId);
}
