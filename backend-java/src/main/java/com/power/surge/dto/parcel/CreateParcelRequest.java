package com.power.surge.dto.parcel;

import java.math.BigDecimal;
import java.util.List;

public record CreateParcelRequest(
        String parcelId,
        String ownerName,
        BigDecimal acquisitionCostPerM2,
        List<List<List<Double>>> coordinates
) {
}
