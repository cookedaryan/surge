package com.power.surge.service;

import com.power.surge.domain.AuditLog;
import com.power.surge.repository.AuditLogRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
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
    void getRecentAuditLogs_returnsTopLogs() {
        AuditLog log = new AuditLog("admin", "PROJECT_CREATED", "PROJECT", "proj-1", "Created project");
        when(auditLogRepository.findTop50ByOrderByTimestampDesc()).thenReturn(List.of(log));

        List<AuditLog> logs = auditLogService.getRecentAuditLogs();

        assertThat(logs).hasSize(1);
    }
}
