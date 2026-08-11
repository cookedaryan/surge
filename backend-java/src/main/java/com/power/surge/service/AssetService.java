package com.power.surge.service;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.power.surge.domain.AssetType;
import com.power.surge.domain.CadastralParcel;
import com.power.surge.domain.EvacuationTower;
import com.power.surge.domain.LineType;
import com.power.surge.domain.Project;
import com.power.surge.domain.ReferenceLine;
import com.power.surge.domain.RestrictedArea;
import com.power.surge.domain.Substation;
import com.power.surge.domain.WtgLocation;
import com.power.surge.domain.WtgStatus;
import com.power.surge.dto.asset.AssetImportPreviewResponse;
import com.power.surge.dto.asset.CommitAssetImportRequest;
import com.power.surge.dto.asset.CreateSubstationRequest;
import com.power.surge.dto.asset.CreateWtgRequest;
import com.power.surge.dto.asset.EvacuationTowerResponse;
import com.power.surge.dto.asset.GeoJsonImportResponse;
import com.power.surge.dto.asset.ProjectAssetsResponse;
import com.power.surge.dto.asset.ReferenceLineResponse;
import com.power.surge.dto.asset.SubstationResponse;
import com.power.surge.dto.asset.WtgResponse;
import com.power.surge.repository.CadastralParcelRepository;
import com.power.surge.repository.EvacuationTowerRepository;
import com.power.surge.repository.ProjectRepository;
import com.power.surge.repository.ReferenceLineRepository;
import com.power.surge.repository.RestrictedAreaRepository;
import com.power.surge.repository.SubstationRepository;
import com.power.surge.repository.WtgLocationRepository;
import com.power.surge.service.classification.AssetClassifier;
import com.power.surge.service.classification.ClassificationResult;
import org.locationtech.jts.geom.Coordinate;
import org.locationtech.jts.geom.GeometryFactory;
import org.locationtech.jts.geom.LineString;
import org.locationtech.jts.geom.Point;
import org.locationtech.jts.geom.Polygon;
import org.locationtech.jts.geom.PrecisionModel;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.EnumMap;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

@Service
@Transactional(readOnly = true)
public class AssetService {

    /** Fallback turbine capacity. Survey KMZ exports carry no capacity data at all. */
    private static final BigDecimal DEFAULT_WTG_CAPACITY_MW = new BigDecimal("3.000");

    /** Matches tower IDs of the form {@code <section>/<index>}, e.g. {@code 20/12}. */
    private static final Pattern TOWER_SECTION = Pattern.compile("^(\\d+)\\s*/\\s*(\\d+)$");
    private static final Pattern ANGLE_POINT = Pattern.compile("^AP[\\s_-]*\\d+$", Pattern.CASE_INSENSITIVE);
    /** "133 KV", "220kV line". */
    private static final Pattern VOLTAGE_CLASS =
            Pattern.compile("(\\d{2,3})\\s*KV\\b", Pattern.CASE_INSENSITIVE);

    private final ProjectRepository projectRepository;
    private final WtgLocationRepository wtgLocationRepository;
    private final SubstationRepository substationRepository;
    private final EvacuationTowerRepository evacuationTowerRepository;
    private final ReferenceLineRepository referenceLineRepository;
    private final CadastralParcelRepository cadastralParcelRepository;
    private final RestrictedAreaRepository restrictedAreaRepository;
    private final AssetClassifier assetClassifier;
    private final AssetImportStagingService stagingService;
    private final ObjectMapper objectMapper;
    private final GeometryFactory geometryFactory = new GeometryFactory(new PrecisionModel(), Project.WGS84_SRID);

    public AssetService(
            ProjectRepository projectRepository,
            WtgLocationRepository wtgLocationRepository,
            SubstationRepository substationRepository,
            EvacuationTowerRepository evacuationTowerRepository,
            ReferenceLineRepository referenceLineRepository,
            CadastralParcelRepository cadastralParcelRepository,
            RestrictedAreaRepository restrictedAreaRepository,
            AssetClassifier assetClassifier,
            AssetImportStagingService stagingService,
            ObjectMapper objectMapper
    ) {
        this.projectRepository = projectRepository;
        this.wtgLocationRepository = wtgLocationRepository;
        this.substationRepository = substationRepository;
        this.evacuationTowerRepository = evacuationTowerRepository;
        this.referenceLineRepository = referenceLineRepository;
        this.cadastralParcelRepository = cadastralParcelRepository;
        this.restrictedAreaRepository = restrictedAreaRepository;
        this.assetClassifier = assetClassifier;
        this.stagingService = stagingService;
        this.objectMapper = objectMapper;
    }

    // ------------------------------------------------------------------
    // Import — preview and commit
    // ------------------------------------------------------------------

    /**
     * Classifies an uploaded FeatureCollection without persisting anything, and stages it for a
     * subsequent {@link #commitImport}.
     */
    public AssetImportPreviewResponse previewImport(
            UUID projectId,
            String fileName,
            Map<String, Object> featureCollection,
            int duplicatesRemoved,
            Map<String, Integer> skippedByGeometry
    ) {
        getProjectOrThrow(projectId);

        List<Map<String, Object>> rawFeatures = toFeatureMaps(featureCollection);
        List<AssetImportPreviewResponse.ClassifiedFeature> classified = new ArrayList<>();
        Map<AssetType, Integer> counts = new EnumMap<>(AssetType.class);

        for (int i = 0; i < rawFeatures.size(); i++) {
            ParsedFeature parsed = parseFeature(rawFeatures.get(i));
            if (parsed == null) {
                continue;
            }
            ClassificationResult result = classify(parsed);
            counts.merge(result.assetType(), 1, Integer::sum);

            LineType lineType = parsed.isLine()
                    ? assetClassifier.classifyLine(
                            parsed.externalId(), parsed.kmlFolderPath(), parsed.explicitType()).lineType()
                    : null;

            classified.add(new AssetImportPreviewResponse.ClassifiedFeature(
                    i,
                    parsed.geometryType(),
                    parsed.externalId(),
                    parsed.kmlFolder(),
                    result.assetType(),
                    lineType,
                    result.status(),
                    result.matchedRule().name(),
                    result.evidence(),
                    parsed.isPoint() ? 1 : parsed.vertices().size(),
                    parsed.longitude(),
                    parsed.latitude()
            ));
        }

        String importId = stagingService.stage(projectId, fileName, rawFeatures);

        return new AssetImportPreviewResponse(
                projectId,
                importId,
                fileName,
                rawFeatures.size(),
                duplicatesRemoved,
                toNameKeyedCounts(counts),
                skippedByGeometry == null ? Map.of() : skippedByGeometry,
                classified
        );
    }

    /** Persists a previously previewed import, applying any user overrides. */
    @Transactional
    public GeoJsonImportResponse commitImport(UUID projectId, CommitAssetImportRequest request) {
        Project project = getProjectOrThrow(projectId);
        AssetImportStagingService.StagedImport staged = stagingService.require(projectId, request.importId());

        GeoJsonImportResponse response = persist(
                project,
                staged.features(),
                request.overridesOrEmpty(),
                request.statusOverridesOrEmpty(),
                request.defaultCapacityMw(),
                request.skipUnclassifiedOrDefault()
        );

        stagingService.discard(request.importId());
        return response;
    }

    /**
     * Single-step import for GeoJSON payloads that already carry explicit asset types.
     *
     * <p>Unclassifiable features are rejected rather than silently defaulted. Before this change the
     * method assumed anything that was not a substation was a turbine, which is what caused
     * evacuation towers to be persisted as 3.0 MW WTGs.</p>
     */
    @Transactional
    public GeoJsonImportResponse importGeoJson(UUID projectId, String geoJsonContent) {
        Project project = getProjectOrThrow(projectId);

        if (geoJsonContent == null || geoJsonContent.isBlank()) {
            throw new IllegalArgumentException("GeoJSON content must not be blank.");
        }

        JsonNode root;
        try {
            root = objectMapper.readTree(geoJsonContent);
        } catch (Exception e) {
            throw new IllegalArgumentException("Invalid GeoJSON format: " + e.getMessage(), e);
        }

        List<Map<String, Object>> features = new ArrayList<>();
        for (JsonNode node : extractFeatures(root)) {
            features.add(objectMapper.convertValue(node, Map.class));
        }

        return persist(project, features, Map.of(), Map.of(), null, false);
    }

    // ------------------------------------------------------------------
    // Persistence
    // ------------------------------------------------------------------

    private GeoJsonImportResponse persist(
            Project project,
            List<Map<String, Object>> rawFeatures,
            Map<String, String> typeOverrides,
            Map<String, String> statusOverrides,
            BigDecimal defaultCapacityMw,
            boolean skipUnclassified
    ) {
        UUID projectId = project.getId();

        Set<String> existingWtgIds = normalisedIds(
                wtgLocationRepository.findAllByProjectIdOrderByExternalIdAsc(projectId).stream()
                        .map(WtgLocation::getExternalId).toList());
        Set<String> existingSubIds = normalisedIds(
                substationRepository.findAllByProjectIdOrderByExternalIdAsc(projectId).stream()
                        .map(Substation::getExternalId).toList());
        Set<String> existingTowerIds = normalisedIds(
                evacuationTowerRepository.findAllByProjectIdOrderByExternalIdAsc(projectId).stream()
                        .map(EvacuationTower::getExternalId).toList());

        List<WtgLocation> wtgEntities = new ArrayList<>();
        List<Substation> substationEntities = new ArrayList<>();
        List<EvacuationTower> towerEntities = new ArrayList<>();
        List<ReferenceLine> lineEntities = new ArrayList<>();
        List<CadastralParcel> parcelEntities = new ArrayList<>();
        List<RestrictedArea> restrictedEntities = new ArrayList<>();
        List<String> unresolvedIds = new ArrayList<>();

        int wtgCounter = existingWtgIds.size() + 1;
        int subCounter = existingSubIds.size() + 1;
        int towerCounter = existingTowerIds.size() + 1;
        int lineCounter = 1;
        int parcelCounter = 1;
        int restrictedCounter = 1;
        int surveySkipped = 0;
        int measurementSkipped = 0;
        int duplicatesSkipped = 0;

        for (Map<String, Object> raw : rawFeatures) {
            ParsedFeature parsed = parseFeature(raw);
            if (parsed == null) {
                continue;
            }

            AssetType assetType = resolveType(parsed, typeOverrides);
            if (assetType == AssetType.UNKNOWN) {
                unresolvedIds.add(describeUnresolved(parsed));
                continue;
            }
            if (assetType == AssetType.SURVEY_POINT) {
                surveySkipped++;
                continue;
            }

            // --- Linear features -------------------------------------------------
            if (parsed.isLine()) {
                LineType lineType = lineTypeFor(parsed, typeOverrides);
                if (!lineType.isImportable()) {
                    // Google Earth "Path Measure" artifacts: counted, not persisted.
                    measurementSkipped++;
                    continue;
                }
                LineString path = geometryFactory.createLineString(
                        parsed.vertices().toArray(new Coordinate[0]));
                path.setSRID(Project.WGS84_SRID);
                lineEntities.add(new ReferenceLine(
                        project,
                        orGenerated(parsed.externalId(), "LINE-%03d", lineCounter++),
                        lineType,
                        path,
                        voltageFrom(parsed.externalId()),
                        null,
                        parsed.kmlFolderPath()));
                continue;
            }

            // --- Areas -----------------------------------------------------------
            if (parsed.isPolygon()) {
                Polygon polygon = buildPolygon(parsed.vertices());
                if (assetType == AssetType.RESTRICTED_AREA) {
                    restrictedEntities.add(new RestrictedArea(
                            project,
                            orGenerated(parsed.externalId(), "ZONE-%03d", restrictedCounter++),
                            restrictionTypeFor(parsed),
                            BigDecimal.ZERO,
                            polygon));
                } else {
                    parcelEntities.add(new CadastralParcel(
                            project,
                            orGenerated(parsed.externalId(), "PARCEL-%03d", parcelCounter++),
                            null,
                            parsed.costPerM2() == null ? BigDecimal.ZERO : parsed.costPerM2(),
                            polygon));
                }
                continue;
            }

            Point point = geometryFactory.createPoint(new Coordinate(parsed.longitude(), parsed.latitude()));

            switch (assetType) {
                case SUBSTATION -> {
                    String externalId = orGenerated(parsed.externalId(), "SUB-%03d", subCounter++);
                    if (!existingSubIds.add(assetClassifier.normaliseId(externalId))) {
                        duplicatesSkipped++;
                        continue;
                    }
                    substationEntities.add(new Substation(project, externalId, parsed.capacityMw(), point));
                }
                case EVACUATION_TOWER -> {
                    String externalId = orGenerated(parsed.externalId(), "TWR-%03d", towerCounter++);
                    if (!existingTowerIds.add(assetClassifier.normaliseId(externalId))) {
                        duplicatesSkipped++;
                        continue;
                    }
                    towerEntities.add(new EvacuationTower(
                            project,
                            externalId,
                            point,
                            towerTypeFor(externalId),
                            parsed.heightM(),
                            lineSectionFor(externalId),
                            parsed.kmlFolderPath()
                    ));
                }
                case WTG -> {
                    String externalId = orGenerated(parsed.externalId(), "WTG-%03d", wtgCounter++);
                    if (!existingWtgIds.add(assetClassifier.normaliseId(externalId))) {
                        duplicatesSkipped++;
                        continue;
                    }
                    BigDecimal capacity = firstNonNull(
                            parsed.capacityMw(), defaultCapacityMw, DEFAULT_WTG_CAPACITY_MW);
                    wtgEntities.add(new WtgLocation(
                            project,
                            externalId,
                            capacity,
                            point,
                            resolveStatus(parsed, statusOverrides),
                            parsed.kmlFolderPath()
                    ));
                }
                case UNKNOWN -> {
                    AssetType inferred = inferTypeFromText(parsed.externalId(), parsed.kmlFolderPath());
                    if (inferred == AssetType.EVACUATION_TOWER) {
                        String externalId = orGenerated(parsed.externalId(), "TWR-%03d", towerCounter++);
                        if (!existingTowerIds.add(assetClassifier.normaliseId(externalId))) {
                            duplicatesSkipped++;
                            continue;
                        }
                        towerEntities.add(new EvacuationTower(
                                project, externalId, point, towerTypeFor(externalId),
                                parsed.heightM(), lineSectionFor(externalId), parsed.kmlFolderPath()
                        ));
                    } else if (inferred == AssetType.SUBSTATION) {
                        String externalId = orGenerated(parsed.externalId(), "SUB-%03d", subCounter++);
                        if (!existingSubIds.add(assetClassifier.normaliseId(externalId))) {
                            duplicatesSkipped++;
                            continue;
                        }
                        substationEntities.add(new Substation(project, externalId, parsed.capacityMw(), point));
                    } else if (inferred == AssetType.WTG) {
                        String externalId = orGenerated(parsed.externalId(), "WTG-%03d", wtgCounter++);
                        if (!existingWtgIds.add(assetClassifier.normaliseId(externalId))) {
                            duplicatesSkipped++;
                            continue;
                        }
                        BigDecimal capacity = firstNonNull(
                                parsed.capacityMw(), defaultCapacityMw, DEFAULT_WTG_CAPACITY_MW);
                        wtgEntities.add(new WtgLocation(
                                project, externalId, capacity, point,
                                resolveStatus(parsed, statusOverrides), parsed.kmlFolderPath()
                        ));
                    } else {
                        unresolvedIds.add(describeUnresolved(parsed));
                    }
                }
                default -> {
                }
            }
        }

        if (!unresolvedIds.isEmpty() && !skipUnclassified) {
            throw new IllegalArgumentException(buildUnclassifiedMessage(unresolvedIds));
        }

        List<WtgLocation> savedWtgs = wtgLocationRepository.saveAll(wtgEntities);
        List<Substation> savedSubstations = substationRepository.saveAll(substationEntities);
        List<EvacuationTower> savedTowers = evacuationTowerRepository.saveAll(towerEntities);
        List<ReferenceLine> savedLines = referenceLineRepository.saveAll(lineEntities);
        List<CadastralParcel> savedParcels = cadastralParcelRepository.saveAll(parcelEntities);
        List<RestrictedArea> savedRestricted = restrictedAreaRepository.saveAll(restrictedEntities);

        Map<String, Integer> countsByType = new LinkedHashMap<>();
        countsByType.put(AssetType.WTG.name(), savedWtgs.size());
        countsByType.put(AssetType.SUBSTATION.name(), savedSubstations.size());
        countsByType.put(AssetType.EVACUATION_TOWER.name(), savedTowers.size());
        countsByType.put(AssetType.REFERENCE_LINE.name(), savedLines.size());
        countsByType.put(AssetType.PARCEL.name(), savedParcels.size());
        countsByType.put(AssetType.RESTRICTED_AREA.name(), savedRestricted.size());
        countsByType.put(AssetType.SURVEY_POINT.name(), surveySkipped);
        countsByType.put(AssetType.UNKNOWN.name(), unresolvedIds.size());

        int total = savedWtgs.size() + savedSubstations.size() + savedTowers.size()
                + savedLines.size() + savedParcels.size() + savedRestricted.size();

        return new GeoJsonImportResponse(
                projectId,
                savedWtgs.size(),
                savedSubstations.size(),
                savedTowers.size(),
                savedLines.size(),
                savedParcels.size(),
                savedRestricted.size(),
                surveySkipped,
                measurementSkipped,
                unresolvedIds.size(),
                duplicatesSkipped,
                total,
                countsByType,
                savedWtgs.stream().map(this::toWtgResponse).toList(),
                savedSubstations.stream().map(this::toSubstationResponse).toList(),
                savedTowers.stream().map(this::toTowerResponse).toList(),
                savedLines.stream().map(this::toLineResponse).toList()
        );
    }

    /** Builds a closed WGS84 ring, appending the first vertex if the source left it open. */
    private Polygon buildPolygon(List<Coordinate> vertices) {
        List<Coordinate> ring = new ArrayList<>(vertices);
        if (!ring.get(0).equals2D(ring.get(ring.size() - 1))) {
            ring.add(new Coordinate(ring.get(0)));
        }
        Polygon polygon = geometryFactory.createPolygon(ring.toArray(new Coordinate[0]));
        polygon.setSRID(Project.WGS84_SRID);
        return polygon;
    }

    /** Water bodies, forests and sanctuaries carry different setbacks, so the type is recorded. */
    private String restrictionTypeFor(ParsedFeature parsed) {
        String haystack = (parsed.externalId() + " " + orEmpty(parsed.kmlFolderPath()))
                .toUpperCase(Locale.ROOT);
        if (haystack.contains("RIVER") || haystack.contains("RESERVOIR")
                || haystack.contains("CANAL") || haystack.contains("TANK")) {
            return "WATER_BODY";
        }
        if (haystack.contains("FOREST") || haystack.contains("SANCTUARY") || haystack.contains("WILDLIFE")) {
            return "PROTECTED_AREA";
        }
        if (haystack.contains("VILLAGE") || haystack.contains("SETTLEMENT")) {
            return "SETTLEMENT";
        }
        if (haystack.contains("RADAR") || haystack.contains("AIRPORT")) {
            return "AVIATION";
        }
        return "RESTRICTED";
    }

    /** Reads a voltage class out of names such as "133 KV" or "220KV Line". */
    private static BigDecimal voltageFrom(String externalId) {
        if (externalId == null) {
            return null;
        }
        Matcher matcher = VOLTAGE_CLASS.matcher(externalId);
        if (!matcher.find()) {
            return null;
        }
        try {
            return new BigDecimal(matcher.group(1));
        } catch (NumberFormatException e) {
            return null;
        }
    }

    /** Unnamed shapes need their geometry mentioned, otherwise the error lists a row of blanks. */
    private static String describeUnresolved(ParsedFeature parsed) {
        String id = parsed.externalId();
        if (id != null && !id.isBlank()) {
            return id;
        }
        return "<unnamed " + parsed.geometryType() + ">";
    }

    private static String orEmpty(String value) {
        return value == null ? "" : value;
    }

    private static AssetType inferTypeFromText(String externalId, String folderPath) {
        String combined = ((externalId != null ? externalId : "") + " " + (folderPath != null ? folderPath : "")).toLowerCase(Locale.ROOT);
        if (combined.contains("tower") || combined.contains("twr") || combined.contains("gantry") || combined.contains("pole") || combined.contains("ap") || combined.contains("angle point") || combined.contains("pylon")) {
            return AssetType.EVACUATION_TOWER;
        }
        if (combined.contains("substation") || combined.contains("pss") || combined.contains("s/s") || combined.contains("ss") || combined.contains("switchyard") || combined.contains("grid") || combined.contains("sub")) {
            return AssetType.SUBSTATION;
        }
        if (combined.contains("wtg") || combined.contains("turbine") || combined.contains("wec") || combined.contains("weg") || combined.contains("wind")) {
            return AssetType.WTG;
        }
        return AssetType.UNKNOWN;
    }

    private String buildUnclassifiedMessage(List<String> unresolvedIds) {
        List<String> sample = unresolvedIds.stream().limit(10).toList();
        return "Could not classify " + unresolvedIds.size() + " feature(s): " + String.join(", ", sample)
                + (unresolvedIds.size() > sample.size() ? ", ..." : "")
                + ". Use the import preview to assign an asset type, or set an explicit "
                + "'assetType' property on these features.";
    }

    /** Dispatches to the point, polygon or line rule chain according to the geometry. */
    private ClassificationResult classify(ParsedFeature parsed) {
        if (parsed.isPolygon()) {
            return assetClassifier.classifyPolygon(
                    parsed.externalId(), parsed.kmlFolderPath(), parsed.explicitType());
        }
        if (parsed.isLine()) {
            AssetClassifier.LineClassification line = assetClassifier.classifyLine(
                    parsed.externalId(), parsed.kmlFolderPath(), parsed.explicitType());
            AssetType type = line.lineType() == LineType.UNKNOWN
                    ? AssetType.UNKNOWN
                    : AssetType.REFERENCE_LINE;
            return new ClassificationResult(type, WtgStatus.UNKNOWN, line.matchedRule(), line.evidence());
        }
        return assetClassifier.classify(parsed.externalId(), parsed.kmlFolderPath(), parsed.explicitType());
    }

    private LineType lineTypeFor(ParsedFeature parsed, Map<String, String> overrides) {
        String override = lookupOverride(overrides, parsed.externalId());
        if (override != null) {
            LineType overridden = LineType.fromNullable(override);
            if (overridden != LineType.UNKNOWN) {
                return overridden;
            }
        }
        return assetClassifier
                .classifyLine(parsed.externalId(), parsed.kmlFolderPath(), parsed.explicitType())
                .lineType();
    }

    private AssetType resolveType(ParsedFeature parsed, Map<String, String> overrides) {
        String override = lookupOverride(overrides, parsed.externalId());
        if (override != null) {
            AssetType overridden = AssetType.fromNullable(override);
            if (overridden != AssetType.UNKNOWN) {
                return overridden;
            }
        }
        return classify(parsed).assetType();
    }

    private WtgStatus resolveStatus(ParsedFeature parsed, Map<String, String> overrides) {
        String override = lookupOverride(overrides, parsed.externalId());
        if (override != null) {
            WtgStatus overridden = WtgStatus.fromNullable(override);
            if (overridden != WtgStatus.UNKNOWN) {
                return overridden;
            }
        }
        return classify(parsed).status();
    }

    private String lookupOverride(Map<String, String> overrides, String externalId) {
        if (overrides.isEmpty() || externalId == null || externalId.isBlank()) {
            return null;
        }
        String direct = overrides.get(externalId);
        if (direct != null) {
            return direct;
        }
        String normalised = assetClassifier.normaliseId(externalId);
        for (Map.Entry<String, String> entry : overrides.entrySet()) {
            if (assetClassifier.normaliseId(entry.getKey()).equals(normalised)) {
                return entry.getValue();
            }
        }
        return null;
    }

    // ------------------------------------------------------------------
    // Direct asset creation
    // ------------------------------------------------------------------

    @Transactional
    public WtgResponse createWtg(UUID projectId, CreateWtgRequest request) {
        Project project = getProjectOrThrow(projectId);
        Point point = geometryFactory.createPoint(new Coordinate(request.longitude(), request.latitude()));
        WtgLocation wtg = new WtgLocation(project, request.externalId(), request.capacityMw(), point);
        return toWtgResponse(wtgLocationRepository.save(wtg));
    }

    @Transactional
    public SubstationResponse createSubstation(UUID projectId, CreateSubstationRequest request) {
        Project project = getProjectOrThrow(projectId);
        Point point = geometryFactory.createPoint(new Coordinate(request.longitude(), request.latitude()));
        Substation substation = new Substation(project, request.externalId(), request.capacityMw(), point);
        return toSubstationResponse(substationRepository.save(substation));
    }

    // ------------------------------------------------------------------
    // Reads
    // ------------------------------------------------------------------

    public ProjectAssetsResponse getProjectAssets(UUID projectId) {
        getProjectOrThrow(projectId);
        List<WtgLocation> wtgEntities = wtgLocationRepository.findAllByProjectIdOrderByExternalIdAsc(projectId);
        List<WtgResponse> wtgs = wtgEntities.stream().map(this::toWtgResponse).toList();
        List<SubstationResponse> substations = substationRepository.findAllByProjectIdOrderByExternalIdAsc(projectId)
                .stream().map(this::toSubstationResponse).toList();
        List<EvacuationTowerResponse> towers = evacuationTowerRepository.findAllByProjectIdOrderByExternalIdAsc(projectId)
                .stream().map(this::toTowerResponse).toList();

        int optimisable = (int) wtgEntities.stream().filter(w -> w.getStatus().isOptimisable()).count();

        return new ProjectAssetsResponse(
                projectId, wtgs.size(), optimisable, substations.size(), towers.size(), wtgs, substations, towers);
    }

    public List<WtgResponse> listWtgs(UUID projectId) {
        getProjectOrThrow(projectId);
        return wtgLocationRepository.findAllByProjectIdOrderByExternalIdAsc(projectId)
                .stream().map(this::toWtgResponse).toList();
    }

    public List<SubstationResponse> listSubstations(UUID projectId) {
        getProjectOrThrow(projectId);
        return substationRepository.findAllByProjectIdOrderByExternalIdAsc(projectId)
                .stream().map(this::toSubstationResponse).toList();
    }

    public List<EvacuationTowerResponse> listTowers(UUID projectId) {
        getProjectOrThrow(projectId);
        return evacuationTowerRepository.findAllByProjectIdOrderByExternalIdAsc(projectId)
                .stream().map(this::toTowerResponse).toList();
    }

    public Map<String, Object> getProjectAssetsGeoJson(UUID projectId) {
        getProjectOrThrow(projectId);
        List<Map<String, Object>> features = new ArrayList<>();

        for (WtgLocation wtg : wtgLocationRepository.findAllByProjectIdOrderByExternalIdAsc(projectId)) {
            Map<String, Object> properties = new LinkedHashMap<>();
            properties.put("assetType", AssetType.WTG.name());
            properties.put("externalId", wtg.getExternalId());
            properties.put("capacityMw", wtg.getCapacityMw());
            properties.put("status", wtg.getStatus().name());
            properties.put("optimisable", wtg.getStatus().isOptimisable());
            if (wtg.getSourceFolder() != null) {
                properties.put("sourceFolder", wtg.getSourceFolder());
            }
            features.add(feature(wtg.getId(), wtg.getLocation(), properties));
        }

        for (Substation sub : substationRepository.findAllByProjectIdOrderByExternalIdAsc(projectId)) {
            Map<String, Object> properties = new LinkedHashMap<>();
            properties.put("assetType", AssetType.SUBSTATION.name());
            properties.put("externalId", sub.getExternalId());
            if (sub.getCapacityMw() != null) {
                properties.put("capacityMw", sub.getCapacityMw());
            }
            features.add(feature(sub.getId(), sub.getLocation(), properties));
        }

        for (EvacuationTower tower : evacuationTowerRepository.findAllByProjectIdOrderByExternalIdAsc(projectId)) {
            Map<String, Object> properties = new LinkedHashMap<>();
            properties.put("assetType", AssetType.EVACUATION_TOWER.name());
            properties.put("externalId", tower.getExternalId());
            if (tower.getTowerType() != null) {
                properties.put("towerType", tower.getTowerType());
            }
            if (tower.getLineSection() != null) {
                properties.put("lineSection", tower.getLineSection());
            }
            if (tower.getHeightM() != null) {
                properties.put("heightM", tower.getHeightM());
            }
            features.add(feature(tower.getId(), tower.getLocation(), properties));
        }

        for (ReferenceLine line : referenceLineRepository.findAllByProjectIdOrderByExternalIdAsc(projectId)) {
            Map<String, Object> properties = new LinkedHashMap<>();
            properties.put("assetType", AssetType.REFERENCE_LINE.name());
            properties.put("externalId", line.getExternalId());
            properties.put("lineType", line.getLineType().name());
            properties.put("crossingConstraint", line.getLineType().isCrossingConstraint());
            if (line.getVoltageKv() != null) {
                properties.put("voltageKv", line.getVoltageKv());
            }

            List<List<Double>> coordinates = new ArrayList<>();
            for (Coordinate coordinate : line.getPath().getCoordinates()) {
                coordinates.add(List.of(coordinate.x, coordinate.y));
            }

            Map<String, Object> geometry = new LinkedHashMap<>();
            geometry.put("type", "LineString");
            geometry.put("coordinates", coordinates);

            Map<String, Object> feature = new LinkedHashMap<>();
            feature.put("type", "Feature");
            feature.put("id", line.getId().toString());
            feature.put("geometry", geometry);
            feature.put("properties", properties);
            features.add(feature);
        }

        Map<String, Object> featureCollection = new LinkedHashMap<>();
        featureCollection.put("type", "FeatureCollection");
        featureCollection.put("features", features);
        return featureCollection;
    }

    public List<ReferenceLineResponse> listLines(UUID projectId) {
        getProjectOrThrow(projectId);
        return referenceLineRepository.findAllByProjectIdOrderByExternalIdAsc(projectId)
                .stream().map(this::toLineResponse).toList();
    }

    // ------------------------------------------------------------------
    // Helpers
    // ------------------------------------------------------------------

    /**
     * A GeoJSON feature reduced to the fields classification and persistence need.
     *
     * <p>{@code vertices} is populated for LineString and Polygon geometries; {@code longitude} and
     * {@code latitude} carry the single coordinate for Points.</p>
     */
    private record ParsedFeature(
            String geometryType,
            String externalId,
            String kmlFolder,
            String kmlFolderPath,
            String explicitType,
            BigDecimal capacityMw,
            BigDecimal heightM,
            BigDecimal costPerM2,
            double longitude,
            double latitude,
            List<Coordinate> vertices
    ) {
        boolean isPoint() {
            return "Point".equalsIgnoreCase(geometryType);
        }

        boolean isLine() {
            return "LineString".equalsIgnoreCase(geometryType);
        }

        boolean isPolygon() {
            return "Polygon".equalsIgnoreCase(geometryType);
        }
    }

    private ParsedFeature parseFeature(Map<String, Object> raw) {
        JsonNode feature = objectMapper.valueToTree(raw);
        JsonNode geometry = feature.get("geometry");
        if (geometry == null || geometry.isNull()) {
            return null;
        }

        String geometryType = geometry.path("type").asText();
        JsonNode coords = geometry.get("coordinates");
        if (coords == null || !coords.isArray() || coords.isEmpty()) {
            return null;
        }

        JsonNode properties = feature.path("properties");
        String externalId = extractString(feature, "id");
        if (externalId == null) {
            externalId = extractString(properties, "externalId", "external_id", "name", "id");
        }

        double longitude = 0;
        double latitude = 0;
        List<Coordinate> vertices = List.of();

        if ("Point".equalsIgnoreCase(geometryType)) {
            if (coords.size() < 2) {
                throw new IllegalArgumentException(
                        "Point geometry must contain valid [longitude, latitude] coordinates.");
            }
            longitude = coords.get(0).asDouble();
            latitude = coords.get(1).asDouble();
            validateCoordinates(longitude, latitude);
        } else if ("LineString".equalsIgnoreCase(geometryType)) {
            vertices = readVertices(coords);
            if (vertices.size() < 2) {
                return null;
            }
        } else if ("Polygon".equalsIgnoreCase(geometryType)) {
            vertices = readVertices(coords.get(0));
            if (vertices.size() < 4) {
                return null;
            }
        } else {
            // MultiGeometry and friends are not supported; they surface in the skipped counts.
            return null;
        }

        return new ParsedFeature(
                geometryType,
                externalId == null ? "" : externalId,
                extractString(properties, "kmlFolder"),
                extractString(properties, "kmlFolderPath", "kmlFolder"),
                extractString(properties, "assetType", "type", "layer"),
                extractDecimal(properties, "capacityMw", "capacity_mw", "capacity", "powerMw", "power"),
                extractDecimal(properties, "heightM", "height_m", "height", "hubHeight"),
                extractDecimal(properties, "acquisitionCostPerM2", "costPerM2", "cost_per_m2"),
                longitude,
                latitude,
                vertices
        );
    }

    private List<Coordinate> readVertices(JsonNode coordinateArray) {
        List<Coordinate> vertices = new ArrayList<>();
        if (coordinateArray == null || !coordinateArray.isArray()) {
            return vertices;
        }
        for (JsonNode vertex : coordinateArray) {
            if (!vertex.isArray() || vertex.size() < 2) {
                continue;
            }
            double lon = vertex.get(0).asDouble();
            double lat = vertex.get(1).asDouble();
            validateCoordinates(lon, lat);
            vertices.add(new Coordinate(lon, lat));
        }
        return vertices;
    }

    private List<Map<String, Object>> toFeatureMaps(Map<String, Object> featureCollection) {
        Object features = featureCollection == null ? null : featureCollection.get("features");
        if (!(features instanceof List<?> list)) {
            throw new IllegalArgumentException("FeatureCollection must contain a 'features' array.");
        }
        List<Map<String, Object>> result = new ArrayList<>();
        for (Object item : list) {
            if (item instanceof Map<?, ?> map) {
                @SuppressWarnings("unchecked")
                Map<String, Object> typed = (Map<String, Object>) map;
                result.add(typed);
            }
        }
        return result;
    }

    /** {@code 20/12} belongs to line section {@code 20}. */
    private static String lineSectionFor(String externalId) {
        Matcher matcher = TOWER_SECTION.matcher(externalId.trim());
        return matcher.matches() ? matcher.group(1) : null;
    }

    private static String towerTypeFor(String externalId) {
        String id = externalId.trim();
        if (id.equalsIgnoreCase("GANTRY")) {
            return "GANTRY";
        }
        if (ANGLE_POINT.matcher(id).matches()) {
            return "ANGLE_POINT";
        }
        if (TOWER_SECTION.matcher(id).matches()) {
            return "SUSPENSION";
        }
        return null;
    }

    private Set<String> normalisedIds(List<String> externalIds) {
        Set<String> normalised = new HashSet<>();
        for (String id : externalIds) {
            normalised.add(assetClassifier.normaliseId(id));
        }
        return normalised;
    }

    private static String orGenerated(String externalId, String template, int counter) {
        if (externalId == null || externalId.isBlank()) {
            return String.format(Locale.ROOT, template, counter);
        }
        String trimmed = externalId.trim();
        return trimmed.length() > 100 ? trimmed.substring(0, 100) : trimmed;
    }

    private static BigDecimal firstNonNull(BigDecimal... values) {
        for (BigDecimal value : values) {
            if (value != null && value.signum() > 0) {
                return value;
            }
        }
        return DEFAULT_WTG_CAPACITY_MW;
    }

    private static Map<String, Integer> toNameKeyedCounts(Map<AssetType, Integer> counts) {
        Map<String, Integer> named = new LinkedHashMap<>();
        for (AssetType type : AssetType.values()) {
            named.put(type.name(), counts.getOrDefault(type, 0));
        }
        return named;
    }

    private Map<String, Object> feature(UUID id, Point location, Map<String, Object> properties) {
        Map<String, Object> geometry = new LinkedHashMap<>();
        geometry.put("type", "Point");
        geometry.put("coordinates", List.of(location.getX(), location.getY()));

        Map<String, Object> feature = new LinkedHashMap<>();
        feature.put("type", "Feature");
        feature.put("id", id.toString());
        feature.put("geometry", geometry);
        feature.put("properties", properties);
        return feature;
    }

    private Project getProjectOrThrow(UUID projectId) {
        return projectRepository.findById(projectId)
                .orElseThrow(() -> new ProjectNotFoundException(projectId));
    }

    private WtgResponse toWtgResponse(WtgLocation wtg) {
        return new WtgResponse(
                wtg.getId(),
                wtg.getExternalId(),
                wtg.getCapacityMw(),
                wtg.getLocation().getX(),
                wtg.getLocation().getY(),
                wtg.getStatus(),
                wtg.getStatus().isOptimisable(),
                wtg.getSourceFolder(),
                wtg.getCreatedAt()
        );
    }

    private SubstationResponse toSubstationResponse(Substation sub) {
        return new SubstationResponse(
                sub.getId(),
                sub.getExternalId(),
                sub.getCapacityMw(),
                sub.getLocation().getX(),
                sub.getLocation().getY(),
                sub.getCreatedAt()
        );
    }

    private EvacuationTowerResponse toTowerResponse(EvacuationTower tower) {
        return new EvacuationTowerResponse(
                tower.getId(),
                tower.getExternalId(),
                tower.getTowerType(),
                tower.getHeightM(),
                tower.getLineSection(),
                tower.getSourceFolder(),
                tower.getLocation().getX(),
                tower.getLocation().getY(),
                tower.getCreatedAt()
        );
    }

    private ReferenceLineResponse toLineResponse(ReferenceLine line) {
        List<List<Double>> coordinates = new ArrayList<>();
        for (Coordinate coordinate : line.getPath().getCoordinates()) {
            coordinates.add(List.of(coordinate.x, coordinate.y));
        }
        return new ReferenceLineResponse(
                line.getId(),
                line.getExternalId(),
                line.getLineType(),
                line.getLineType().isCrossingConstraint(),
                line.getVoltageKv(),
                line.getLengthM(),
                line.getSourceFolder(),
                coordinates,
                line.getCreatedAt()
        );
    }

    private static List<JsonNode> extractFeatures(JsonNode root) {
        String type = root.path("type").asText();
        List<JsonNode> list = new ArrayList<>();
        if ("FeatureCollection".equalsIgnoreCase(type)) {
            JsonNode features = root.get("features");
            if (features != null && features.isArray()) {
                features.forEach(list::add);
            }
        } else if ("Feature".equalsIgnoreCase(type)) {
            list.add(root);
        } else {
            throw new IllegalArgumentException(
                    "GeoJSON root type must be 'FeatureCollection' or 'Feature'. Got: " + type);
        }
        return list;
    }

    private static String extractString(JsonNode node, String... keys) {
        if (node == null || node.isMissingNode() || node.isNull()) {
            return null;
        }
        for (String key : keys) {
            JsonNode val = node.get(key);
            if (val != null && !val.isNull() && !val.asText().isBlank()) {
                return val.asText().trim();
            }
        }
        return null;
    }

    private static BigDecimal extractDecimal(JsonNode properties, String... keys) {
        if (properties == null || properties.isMissingNode() || properties.isNull()) {
            return null;
        }
        for (String key : keys) {
            JsonNode val = properties.get(key);
            if (val == null || val.isNull()) {
                continue;
            }
            if (val.isNumber()) {
                return val.decimalValue();
            }
            if (val.isTextual() && !val.asText().isBlank()) {
                try {
                    return new BigDecimal(val.asText().trim());
                } catch (NumberFormatException ignored) {
                    // Non-numeric text such as "3.5 MW" is treated as absent.
                }
            }
        }
        return null;
    }

    private static void validateCoordinates(double lon, double lat) {
        if (lon < -180.0 || lon > 180.0) {
            throw new IllegalArgumentException("Longitude must be between -180 and 180 degrees. Got: " + lon);
        }
        if (lat < -90.0 || lat > 90.0) {
            throw new IllegalArgumentException("Latitude must be between -90 and 90 degrees. Got: " + lat);
        }
    }
}
