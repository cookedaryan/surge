package com.power.surge.dto.restriction;

import com.power.surge.domain.RestrictedArea;
import org.locationtech.jts.geom.Coordinate;
import org.locationtech.jts.geom.LineString;

import java.math.BigDecimal;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

public record RestrictedAreaResponse(
        UUID id,
        UUID projectId,
        String name,
        String restrictionType,
        BigDecimal bufferMeters,
        List<List<List<Double>>> coordinates,
        Instant createdAt
) {
    public static RestrictedAreaResponse fromEntity(RestrictedArea area) {
        List<List<List<Double>>> rings = new ArrayList<>();
        if (area.getGeometry() != null) {
            LineString extRing = area.getGeometry().getExteriorRing();
            List<List<Double>> exterior = new ArrayList<>();
            for (Coordinate c : extRing.getCoordinates()) {
                exterior.add(List.of(c.getX(), c.getY()));
            }
            rings.add(exterior);

            for (int i = 0; i < area.getGeometry().getNumInteriorRing(); i++) {
                LineString hole = area.getGeometry().getInteriorRingN(i);
                List<List<Double>> holeCoords = new ArrayList<>();
                for (Coordinate c : hole.getCoordinates()) {
                    holeCoords.add(List.of(c.getX(), c.getY()));
                }
                rings.add(holeCoords);
            }
        }

        return new RestrictedAreaResponse(
                area.getId(),
                area.getProject().getId(),
                area.getName(),
                area.getRestrictionType(),
                area.getBufferMeters(),
                rings,
                area.getCreatedAt()
        );
    }
}
