package com.power.surge.dto.parcel;

import com.power.surge.domain.CadastralParcel;
import org.locationtech.jts.geom.Coordinate;
import org.locationtech.jts.geom.LineString;

import java.math.BigDecimal;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

public record ParcelResponse(
        UUID id,
        UUID projectId,
        String parcelId,
        String ownerName,
        BigDecimal acquisitionCostPerM2,
        List<List<List<Double>>> coordinates,
        Instant createdAt
) {
    public static ParcelResponse fromEntity(CadastralParcel parcel) {
        List<List<List<Double>>> rings = new ArrayList<>();
        if (parcel.getGeometry() != null) {
            LineString extRing = parcel.getGeometry().getExteriorRing();
            List<List<Double>> exterior = new ArrayList<>();
            for (Coordinate c : extRing.getCoordinates()) {
                exterior.add(List.of(c.getX(), c.getY()));
            }
            rings.add(exterior);

            for (int i = 0; i < parcel.getGeometry().getNumInteriorRing(); i++) {
                LineString hole = parcel.getGeometry().getInteriorRingN(i);
                List<List<Double>> holeCoords = new ArrayList<>();
                for (Coordinate c : hole.getCoordinates()) {
                    holeCoords.add(List.of(c.getX(), c.getY()));
                }
                rings.add(holeCoords);
            }
        }

        return new ParcelResponse(
                parcel.getId(),
                parcel.getProject().getId(),
                parcel.getParcelId(),
                parcel.getOwnerName(),
                parcel.getAcquisitionCostPerM2(),
                rings,
                parcel.getCreatedAt()
        );
    }
}
