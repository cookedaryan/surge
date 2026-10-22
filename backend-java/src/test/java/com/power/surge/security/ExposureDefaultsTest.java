package com.power.surge.security;

import com.power.surge.service.AuthService;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.core.env.Environment;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.servlet.MockMvc;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;

/**
 * Defaults that decide what an unauthenticated caller, or a log reader, can learn.
 *
 * <p>Both were left wide open: the health endpoint is deliberately public so a load balancer can
 * probe it, but {@code show-details: always} made it describe the database and disk to anyone; and
 * Hibernate was configured to log every bound parameter in every profile, which writes password
 * hashes, e-mail addresses and imported survey text into the logs.
 */
@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("test")
class ExposureDefaultsTest {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private Environment environment;

    // The first-administrator seeding refuses to run without a password; it is not under test here.
    @MockBean
    private AuthService authService;

    @Test
    void anonymousHealthProbeDoesNotDescribeTheInfrastructure() throws Exception {
        mockMvc.perform(get("/actuator/health"))
                .andExpect(jsonPath("$.status").exists())
                .andExpect(jsonPath("$.components").doesNotExist());
    }

    @Test
    void boundSqlParametersAreNotLoggedByDefault() {
        assertThat(environment.getProperty("logging.level.org.hibernate.type.descriptor.sql.BasicBinder"))
                .as("bind-value logging belongs in the dev profile only")
                .isNull();
        assertThat(environment.getProperty("logging.level.org.hibernate.SQL"))
                .as("statement logging belongs in the dev profile only")
                .isNull();
    }
}
