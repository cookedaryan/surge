package com.power.surge.repository;

import com.power.surge.domain.LineType;
import com.power.surge.domain.ReferenceLine;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;
import java.util.UUID;

public interface ReferenceLineRepository extends JpaRepository<ReferenceLine, UUID> {

    List<ReferenceLine> findAllByProjectIdOrderByExternalIdAsc(UUID projectId);

    List<ReferenceLine> findAllByProjectIdAndLineTypeOrderByExternalIdAsc(UUID projectId, LineType lineType);
}
