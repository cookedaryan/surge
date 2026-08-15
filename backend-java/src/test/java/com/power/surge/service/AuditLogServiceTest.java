package com.power.surge.service;

import com.power.surge.domain.AuditLog;
import com.power.surge.repository.AuditLogRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.dao.DataAccessResourceFailureException;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.core.context.SecurityContextHolder;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatCode;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class AuditLogServiceTest {

    @Mock
    private AuditLogRepository auditLogRepository;

    private AuditLogService auditLogService;

    @BeforeEach
    void setUp() {
        auditLogService = new AuditLogService(auditLogRepository);
    }

    @Test
    void recordAudit_savesAuditEntry() {
        AuditLog log = new AuditLog("admin", "PROJECT_CREATED", "PROJECT", "proj-1", "Created project");
        when(auditLogRepository.save(any(AuditLog.class))).thenReturn(log);

        AuditLog saved = auditLogService.recordAudit("admin", "PROJECT_CREATED", "PROJECT", "proj-1", "Created project");

        assertThat(saved).isNotNull();
        assertThat(saved.getUsername()).isEqualTo("admin");
        assertThat(saved.getAction()).isEqualTo("PROJECT_CREATED");
    }

    @Test
    void record_attributesTheEntryToTheAuthenticatedCaller() {
        SecurityContextHolder.getContext().setAuthentication(
                new UsernamePasswordAuthenticationToken("priya", null,
                        List.of(new SimpleGrantedAuthority("ROLE_ENGINEER"))));
        try {
            auditLogService.record("PROJECT_CREATED", "PROJECT", "proj-1", "Created project");

            ArgumentCaptor<AuditLog> captor = ArgumentCaptor.forClass(AuditLog.class);
            verify(auditLogRepository).save(captor.capture());
            assertThat(captor.getValue().getUsername()).isEqualTo("priya");
            assertThat(captor.getValue().getAction()).isEqualTo("PROJECT_CREATED");
        } finally {
            SecurityContextHolder.clearContext();
        }
    }

    @Test
    void record_fallsBackToAnonymousWhenThereIsNoAuthenticatedCaller() {
        SecurityContextHolder.clearContext();

        auditLogService.record("PROJECT_CREATED", "PROJECT", "proj-1", "Created project");

        ArgumentCaptor<AuditLog> captor = ArgumentCaptor.forClass(AuditLog.class);
        verify(auditLogRepository).save(captor.capture());
        assertThat(captor.getValue().getUsername()).isEqualTo("anonymous");
    }

    /**
     * Audit logging is observability, not business logic: if the write fails, the operation being
     * recorded must still succeed rather than being taken down by its own bookkeeping.
     */
    @Test
    void record_neverPropagatesAStorageFailureToTheCaller() {
        when(auditLogRepository.save(any(AuditLog.class)))
                .thenThrow(new DataAccessResourceFailureException("database unavailable"));

        assertThatCode(() -> auditLogService.record("PROJECT_CREATED", "PROJECT", "proj-1", "Created"))
                .doesNotThrowAnyException();
    }

    @Test
    void getRecentAuditLogs_returnsTopLogs() {
        AuditLog log = new AuditLog("admin", "PROJECT_CREATED", "PROJECT", "proj-1", "Created project");
        when(auditLogRepository.findTop50ByOrderByTimestampDesc()).thenReturn(List.of(log));

        List<AuditLog> logs = auditLogService.getRecentAuditLogs();

        assertThat(logs).hasSize(1);
    }
}
