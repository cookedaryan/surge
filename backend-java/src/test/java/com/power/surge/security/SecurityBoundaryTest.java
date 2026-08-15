package com.power.surge.security;

import com.power.surge.domain.UserRole;
import com.power.surge.dto.auth.AuthResponse;
import com.power.surge.service.AuthService;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.http.MediaType;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.servlet.MockMvc;

import java.util.UUID;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Exercises the real security filter chain.
 *
 * <p>Every other controller test runs with {@code addFilters = false}, so none of them can catch a
 * regression in {@link com.power.surge.config.SecurityConfig}. This one deliberately leaves the
 * filters on and mints genuine tokens through {@link JwtTokenProvider}, so an accidental
 * {@code permitAll} — the state this codebase shipped in until the project routes were locked
 * down — fails the build instead of silently exposing the API.
 */
@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("test")
class SecurityBoundaryTest {

    private static final String PROJECT_ID = "11111111-1111-1111-1111-111111111111";
    private static final String JOB_ID = "22222222-2222-2222-2222-222222222222";

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private JwtTokenProvider tokenProvider;

    @MockBean
    private AuthService authService;

    private String bearer(UserRole role) {
        return "Bearer " + tokenProvider.generateToken(UUID.randomUUID(), "someone", role);
    }

    // --- anonymous access -------------------------------------------------

    @Test
    void projectRoutesRejectAnonymousCallers() throws Exception {
        mockMvc.perform(get("/api/v1/projects"))
                .andExpect(status().isUnauthorized());
    }

    @Test
    void projectScopedResourcesRejectAnonymousCallers() throws Exception {
        mockMvc.perform(get("/api/v1/projects/" + PROJECT_ID + "/jobs"))
                .andExpect(status().isUnauthorized());
    }

    /**
     * The progress stream is the endpoint most likely to be re-opened by accident, because the
     * browser EventSource API cannot send an Authorization header. The client streams it over
     * fetch precisely so this can stay closed.
     */
    @Test
    void jobProgressStreamRejectsAnonymousCallers() throws Exception {
        mockMvc.perform(get("/api/v1/projects/" + PROJECT_ID + "/jobs/" + JOB_ID + "/progress"))
                .andExpect(status().isUnauthorized());
    }

    @Test
    void reportsRejectAnonymousCallers() throws Exception {
        mockMvc.perform(get("/api/v1/projects/" + PROJECT_ID + "/reports/bom"))
                .andExpect(status().isUnauthorized());
    }

    @Test
    void auditLogRejectsAnonymousCallers() throws Exception {
        mockMvc.perform(get("/api/v1/audit-logs"))
                .andExpect(status().isUnauthorized());
    }

    // --- registration is administrator-only -------------------------------

    @Test
    void registrationRejectsAnonymousCallers() throws Exception {
        mockMvc.perform(post("/api/v1/auth/register")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {"username":"intruder","email":"intruder@example.com","password":"hunter2000"}"""))
                .andExpect(status().isUnauthorized());
    }

    /**
     * A self-served account would defeat every other rule here: the caller would simply register,
     * receive a valid token, and access the whole API legitimately.
     */
    @Test
    void registrationRejectsNonAdministrators() throws Exception {
        mockMvc.perform(post("/api/v1/auth/register")
                        .header("Authorization", bearer(UserRole.ROLE_ENGINEER))
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {"username":"intruder","email":"intruder@example.com","password":"hunter2000"}"""))
                .andExpect(status().isForbidden());
    }

    @Test
    void registrationIsAllowedForAdministrators() throws Exception {
        when(authService.register(any())).thenReturn(
                new AuthResponse("token", "newcomer", "newcomer@example.com", UserRole.ROLE_ENGINEER));

        mockMvc.perform(post("/api/v1/auth/register")
                        .header("Authorization", bearer(UserRole.ROLE_ADMIN))
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {"username":"newcomer","email":"newcomer@example.com","password":"hunter2000"}"""))
                .andExpect(status().isCreated());
    }

    // --- account administration is administrator-only ---------------------

    @Test
    void adminUserRoutesRejectAnonymousCallers() throws Exception {
        mockMvc.perform(get("/api/v1/admin/users"))
                .andExpect(status().isUnauthorized());
    }

    @Test
    void adminUserRoutesRejectNonAdministrators() throws Exception {
        mockMvc.perform(get("/api/v1/admin/users").header("Authorization", bearer(UserRole.ROLE_ENGINEER)))
                .andExpect(status().isForbidden());
    }

    @Test
    void aViewerCannotProvisionAccounts() throws Exception {
        mockMvc.perform(post("/api/v1/admin/users")
                        .header("Authorization", bearer(UserRole.ROLE_VIEWER))
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {"username":"newcomer","email":"n@example.com","password":"a-good-password","role":"ROLE_ADMIN"}"""))
                .andExpect(status().isForbidden());
    }

    // --- what must stay reachable ----------------------------------------

    @Test
    void loginRemainsAnonymouslyReachable() throws Exception {
        when(authService.login(any())).thenReturn(
                new AuthResponse("token", "admin", "admin@surge.energy", UserRole.ROLE_ADMIN));

        mockMvc.perform(post("/api/v1/auth/login")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {"username":"admin","password":"admin"}"""))
                .andExpect(status().isOk());
    }

    @Test
    void healthRemainsAnonymouslyReachableForContainerProbes() throws Exception {
        mockMvc.perform(get("/api/v1/health"))
                .andExpect(status().isOk());
    }

    @Test
    void anAuthenticatedCallerReachesProjectRoutes() throws Exception {
        mockMvc.perform(get("/api/v1/projects").header("Authorization", bearer(UserRole.ROLE_ENGINEER)))
                .andExpect(status().isOk());
    }
}
