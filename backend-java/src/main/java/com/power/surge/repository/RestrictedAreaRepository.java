package com.power.surge.repository;

import com.power.surge.domain.RestrictedArea;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;
import java.util.UUID;

public interface RestrictedAreaRepository extends JpaRepository<RestrictedArea, UUID> {

    List<RestrictedArea> findAllByProjectIdOrderByNameAsc(UUID projectId);
}
