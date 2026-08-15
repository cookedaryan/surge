package com.power.surge.service;

import com.power.surge.domain.User;
import com.power.surge.domain.UserRole;
import com.power.surge.dto.admin.CreateUserRequest;
import com.power.surge.dto.admin.ResetPasswordRequest;
import com.power.surge.dto.admin.UpdateUserRequest;
import com.power.surge.dto.admin.UserSummaryResponse;
import com.power.surge.repository.UserRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.test.util.ReflectionTestUtils;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class UserAdminServiceTest {

    @Mock
    private UserRepository userRepository;

    @Mock
    private AuditLogService auditLogService;

    private final PasswordEncoder passwordEncoder = new BCryptPasswordEncoder();
    private UserAdminService service;

    private static final String ACTING_ADMIN = "admin";

    @BeforeEach
    void setUp() {
        service = new UserAdminService(userRepository, passwordEncoder, auditLogService);
    }

    private static User user(String username, UserRole role, boolean enabled) {
        User u = new User(username, username + "@example.com", "hash", role);
        u.setEnabled(enabled);
        ReflectionTestUtils.setField(u, "id", UUID.randomUUID());
        return u;
    }

    // --- creation ---------------------------------------------------------

    @Test
    void createsAnAccountWithAHashedPassword() {
        when(userRepository.existsByUsername("newcomer")).thenReturn(false);
        when(userRepository.existsByEmail("newcomer@example.com")).thenReturn(false);
        when(userRepository.save(any(User.class))).thenAnswer(inv -> {
            User saved = inv.getArgument(0);
            ReflectionTestUtils.setField(saved, "id", UUID.randomUUID());
            return saved;
        });

        UserSummaryResponse created = service.createUser(new CreateUserRequest(
                "newcomer", "newcomer@example.com", "a-good-password", UserRole.ROLE_ENGINEER), ACTING_ADMIN);

        assertThat(created.username()).isEqualTo("newcomer");
        assertThat(created.role()).isEqualTo(UserRole.ROLE_ENGINEER);
        assertThat(created.enabled()).isTrue();
        verify(auditLogService).recordAudit(eq(ACTING_ADMIN), eq("USER_CREATED"), eq("USER"), anyString(), anyString());
    }

    @Test
    void refusesADuplicateUsername() {
        when(userRepository.existsByUsername("taken")).thenReturn(true);

        assertThatThrownBy(() -> service.createUser(new CreateUserRequest(
                "taken", "t@example.com", "a-good-password", UserRole.ROLE_ENGINEER), ACTING_ADMIN))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("already taken");

        verify(userRepository, never()).save(any(User.class));
    }

    // --- self-lockout protection -----------------------------------------

    @Test
    void anAdministratorCannotSuspendTheirOwnAccount() {
        User self = user(ACTING_ADMIN, UserRole.ROLE_ADMIN, true);
        when(userRepository.findById(self.getId())).thenReturn(Optional.of(self));

        assertThatThrownBy(() -> service.updateUser(self.getId(), new UpdateUserRequest(null, false), ACTING_ADMIN))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("your own account");

        assertThat(self.isEnabled()).isTrue();
    }

    @Test
    void anAdministratorCannotChangeTheirOwnRole() {
        User self = user(ACTING_ADMIN, UserRole.ROLE_ADMIN, true);
        when(userRepository.findById(self.getId())).thenReturn(Optional.of(self));

        assertThatThrownBy(() -> service.updateUser(
                self.getId(), new UpdateUserRequest(UserRole.ROLE_VIEWER, null), ACTING_ADMIN))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("your own role");

        assertThat(self.getRole()).isEqualTo(UserRole.ROLE_ADMIN);
    }

    // --- last-administrator protection ------------------------------------

    /** Recovering from zero administrators requires direct database access. Refuse to get there. */
    @Test
    void theLastEnabledAdministratorCannotBeSuspended() {
        User other = user("other-admin", UserRole.ROLE_ADMIN, true);
        when(userRepository.findById(other.getId())).thenReturn(Optional.of(other));
        when(userRepository.countByRoleAndEnabledTrue(UserRole.ROLE_ADMIN)).thenReturn(1L);

        assertThatThrownBy(() -> service.updateUser(other.getId(), new UpdateUserRequest(null, false), ACTING_ADMIN))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("only remaining administrator");

        assertThat(other.isEnabled()).isTrue();
    }

    @Test
    void theLastEnabledAdministratorCannotBeDemoted() {
        User other = user("other-admin", UserRole.ROLE_ADMIN, true);
        when(userRepository.findById(other.getId())).thenReturn(Optional.of(other));
        when(userRepository.countByRoleAndEnabledTrue(UserRole.ROLE_ADMIN)).thenReturn(1L);

        assertThatThrownBy(() -> service.updateUser(
                other.getId(), new UpdateUserRequest(UserRole.ROLE_ENGINEER, null), ACTING_ADMIN))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("only remaining administrator");

        assertThat(other.getRole()).isEqualTo(UserRole.ROLE_ADMIN);
    }

    @Test
    void anAdministratorCanBeSuspendedWhileAnotherRemains() {
        User other = user("other-admin", UserRole.ROLE_ADMIN, true);
        when(userRepository.findById(other.getId())).thenReturn(Optional.of(other));
        when(userRepository.countByRoleAndEnabledTrue(UserRole.ROLE_ADMIN)).thenReturn(2L);
        when(userRepository.save(any(User.class))).thenAnswer(inv -> inv.getArgument(0));

        UserSummaryResponse updated =
                service.updateUser(other.getId(), new UpdateUserRequest(null, false), ACTING_ADMIN);

        assertThat(updated.enabled()).isFalse();
        verify(auditLogService).recordAudit(eq(ACTING_ADMIN), eq("USER_SUSPENDED"), eq("USER"), anyString(), anyString());
    }

    // --- ordinary updates -------------------------------------------------

    @Test
    void suspendingANonAdministratorNeedsNoAdministratorHeadcount() {
        User engineer = user("engineer", UserRole.ROLE_ENGINEER, true);
        when(userRepository.findById(engineer.getId())).thenReturn(Optional.of(engineer));
        when(userRepository.save(any(User.class))).thenAnswer(inv -> inv.getArgument(0));

        UserSummaryResponse updated =
                service.updateUser(engineer.getId(), new UpdateUserRequest(null, false), ACTING_ADMIN);

        assertThat(updated.enabled()).isFalse();
        verify(userRepository, never()).countByRoleAndEnabledTrue(any());
    }

    @Test
    void reinstatingASuspendedAccountIsAudited() {
        User engineer = user("engineer", UserRole.ROLE_ENGINEER, false);
        when(userRepository.findById(engineer.getId())).thenReturn(Optional.of(engineer));
        when(userRepository.save(any(User.class))).thenAnswer(inv -> inv.getArgument(0));

        UserSummaryResponse updated =
                service.updateUser(engineer.getId(), new UpdateUserRequest(null, true), ACTING_ADMIN);

        assertThat(updated.enabled()).isTrue();
        verify(auditLogService).recordAudit(eq(ACTING_ADMIN), eq("USER_REINSTATED"), eq("USER"), anyString(), anyString());
    }

    @Test
    void anUnchangedFieldIsNotAudited() {
        User engineer = user("engineer", UserRole.ROLE_ENGINEER, true);
        when(userRepository.findById(engineer.getId())).thenReturn(Optional.of(engineer));
        when(userRepository.save(any(User.class))).thenAnswer(inv -> inv.getArgument(0));

        service.updateUser(engineer.getId(), new UpdateUserRequest(UserRole.ROLE_ENGINEER, true), ACTING_ADMIN);

        verify(auditLogService, never()).recordAudit(anyString(), anyString(), anyString(), anyString(), anyString());
    }

    // --- password reset ---------------------------------------------------

    @Test
    void resetStoresAHashAndNeverLogsThePassword() {
        User engineer = user("engineer", UserRole.ROLE_ENGINEER, true);
        when(userRepository.findById(engineer.getId())).thenReturn(Optional.of(engineer));
        when(userRepository.save(any(User.class))).thenAnswer(inv -> inv.getArgument(0));

        service.resetPassword(engineer.getId(), new ResetPasswordRequest("brand-new-password"), ACTING_ADMIN);

        assertThat(engineer.getPasswordHash()).isNotEqualTo("brand-new-password");
        assertThat(passwordEncoder.matches("brand-new-password", engineer.getPasswordHash())).isTrue();
        verify(auditLogService).recordAudit(eq(ACTING_ADMIN), eq("USER_PASSWORD_RESET"), eq("USER"),
                anyString(), eq("Password reset for account 'engineer'"));
    }

    @Test
    void listingReturnsAccountsWithoutAnyPasswordMaterial() {
        when(userRepository.findAllByOrderByUsernameAsc())
                .thenReturn(List.of(user("aaa", UserRole.ROLE_ADMIN, true), user("bbb", UserRole.ROLE_VIEWER, false)));

        List<UserSummaryResponse> users = service.listUsers();

        assertThat(users).hasSize(2);
        assertThat(users.get(0).username()).isEqualTo("aaa");
        assertThat(users.get(1).enabled()).isFalse();
        assertThat(UserSummaryResponse.class.getRecordComponents())
                .noneMatch(c -> c.getName().toLowerCase().contains("password"));
    }
}
