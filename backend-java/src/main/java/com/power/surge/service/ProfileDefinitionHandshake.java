package com.power.surge.service;

import com.power.surge.client.PythonProfileClient;
import com.power.surge.dto.client.python.PythonDefinitionHashResponse;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.InitializingBean;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

/**
 * Contract C7 step 2: at startup, when profiles are enabled, Java and Python must agree on which
 * profile definitions are in force.
 *
 * <p>Python owns the definitions; Java holds only a hash of them, set as configuration at FRZ-1. If
 * the two disagree, every ranked result Java serves is produced under a policy Java does not know
 * about — the run would succeed, the numbers would look reasonable, and the recommendation would be
 * attributed to the wrong policy. That is a failure nobody would notice from the outside, so it is
 * caught here, once, rather than per request.
 *
 * <p><b>Startup, not a request.</b> Failing individual requests would leave the service up and
 * apparently healthy while refusing work; failing to start is visible immediately and to the thing
 * that deploys it. An unreachable endpoint fails too, for the same reason: "cannot verify" is not
 * "verified".
 *
 * <p>The check runs as {@code afterPropertiesSet}, so a mismatch stops the context before the web
 * server begins accepting connections. A later hook would let the service answer for the moment
 * between opening the port and giving up.
 */
@Component
public class ProfileDefinitionHandshake implements InitializingBean {

    private static final Logger log = LoggerFactory.getLogger(ProfileDefinitionHandshake.class);

    private final PythonProfileClient profileClient;
    private final boolean profilesEnabled;
    private final String expectedDefinitionHash;

    public ProfileDefinitionHandshake(
            PythonProfileClient profileClient,
            // The same switch Python reads (C5). One deployment, one answer to "are profiles on".
            @Value(OptimisationProfile.ENABLED_PROPERTY) boolean profilesEnabled,
            // No default, deliberately. FRZ-1 sets this; until then, a deployment that turns
            // profiles on has nothing to verify against, and starting anyway would be the silent
            // half of exactly the failure this class exists to prevent.
            @Value("${surge.profiles.expected-definition-hash:}") String expectedDefinitionHash
    ) {
        this.profileClient = profileClient;
        this.profilesEnabled = profilesEnabled;
        this.expectedDefinitionHash = expectedDefinitionHash;
    }

    @Override
    public void afterPropertiesSet() {
        if (!profilesEnabled) {
            // C7 puts the "when profiles are enabled" condition on Java's side. Python answers the
            // endpoint either way (WP3-6a), so nothing here depends on the engine's own flag.
            log.debug("Profiles are disabled; skipping the definition-hash handshake.");
            return;
        }

        if (expectedDefinitionHash == null || expectedDefinitionHash.isBlank()) {
            throw new IllegalStateException(
                    "Profiles are enabled but surge.profiles.expected-definition-hash is not set. "
                            + "The expected hash is configuration, fixed at the FRZ-1 policy freeze; "
                            + "without it there is nothing to check the engine's policy against.");
        }

        PythonDefinitionHashResponse published;
        try {
            published = profileClient.definitionHash();
        } catch (RuntimeException e) {
            throw new IllegalStateException(
                    "Could not reach the optimisation engine's definition-hash endpoint. "
                            + "Profiles are enabled, so the policy in force cannot be confirmed.", e);
        }

        if (published == null || published.definitionHash() == null
                || published.definitionHash().isBlank()) {
            throw new IllegalStateException(
                    "The optimisation engine's definition-hash endpoint returned no definition_hash. "
                            + "Profiles are enabled, so the policy in force cannot be confirmed.");
        }

        if (!expectedDefinitionHash.equals(published.definitionHash())) {
            throw new IllegalStateException(
                    "Profile definition hash mismatch. Expected " + expectedDefinitionHash
                            + " but the optimisation engine published " + published.definitionHash()
                            + ". One side is running policy definitions the other does not have; "
                            + "deploy a matching engine or update the expected hash.");
        }

        log.info("Profile definition hash agreed: {} (metric registry {}, contract pack {}).",
                published.definitionHash(),
                published.metricRegistryVersion(),
                published.contractPackVersion());
    }
}
