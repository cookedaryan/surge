package com.power.surge.repository;

import com.power.surge.domain.WtgLocation;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;
import java.util.UUID;

public interface WtgLocationRepository extends JpaRepository<WtgLocation, UUID> {

    List<WtgLocation> findAllByProjectIdOrderByExternalIdAsc(UUID projectId);
}
