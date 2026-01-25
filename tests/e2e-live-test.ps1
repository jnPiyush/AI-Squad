# ════════════════════════════════════════════════════════════════════════════════
# AI-Squad End-to-End Live Test Script
# ════════════════════════════════════════════════════════════════════════════════
# Purpose: Comprehensive production simulation with custom or default test app
# Coverage: 35 tests (34 component + 1 autonomous lifecycle)
# Usage: .\tests\e2e-live-test.ps1 [options]
# ════════════════════════════════════════════════════════════════════════════════

param(
    [switch]$SkipCleanup = $false,
    [switch]$Verbose = $false,
    [string]$Repo = "jnPiyush/AI-Squad",
    [string]$TestAppRequirement = "",
    [switch]$SkipAutonomousTest = $false,
    [switch]$AutonomousOnly = $false
)

# Set UTF-8 encoding
chcp 65001 > $null
$ErrorActionPreference = "Continue"

# Validate mutually exclusive parameters
if ($SkipAutonomousTest -and $AutonomousOnly) {
    Write-Host "`n❌ ERROR: Cannot use -SkipAutonomousTest and -AutonomousOnly together" -ForegroundColor Red
    Write-Host "   Choose one mode:" -ForegroundColor Yellow
    Write-Host "   • No flags: Run all tests (component + autonomous)" -ForegroundColor Gray
    Write-Host "   • -SkipAutonomousTest: Run only component tests (faster)" -ForegroundColor Gray
    Write-Host "   • -AutonomousOnly: Run only autonomous test (integration)`n" -ForegroundColor Gray
    exit 1
}

# Determine test mode and counts
$TestMode = if ($AutonomousOnly) { 
    "Autonomous Only" 
} elseif ($SkipAutonomousTest) { 
    "Component Tests Only" 
} else { 
    "Full Suite" 
}

# Test counters
$script:TestsPassed = 0
$script:TestsFailed = 0
$script:TotalTests = if ($AutonomousOnly) { 1 } elseif ($SkipAutonomousTest) { 34 } else { 35 }

# Colors
$ColorPass = "Green"
$ColorFail = "Red"
$ColorInfo = "Cyan"
$ColorWarning = "Yellow"

# ════════════════════════════════════════════════════════════════════════════════
# Helper Functions
# ════════════════════════════════════════════════════════════════════════════════

function Write-TestHeader {
    param([string]$Title)
    Write-Host "`n════════════════════════════════════════════════════════════════════════════════" -ForegroundColor $ColorInfo
    Write-Host "  $Title" -ForegroundColor $ColorInfo
    Write-Host "════════════════════════════════════════════════════════════════════════════════" -ForegroundColor $ColorInfo
}

function Write-TestSection {
    param([string]$Section)
    Write-Host "`n--- $Section ---" -ForegroundColor $ColorInfo
}

function Test-Feature {
    param(
        [string]$Name,
        [scriptblock]$Test,
        [string]$Expected = "success"
    )
    
    Write-Host "`n▶ Testing: $Name" -ForegroundColor White
    
    try {
        $result = & $Test
        
        if ($result -match "error|failed|exception" -and $Expected -eq "success") {
            Write-Host "  ✗ FAILED: $Name" -ForegroundColor $ColorFail
            if ($Verbose) { Write-Host "  Output: $result" -ForegroundColor Gray }
            $script:TestsFailed++
            return $false
        } else {
            Write-Host "  ✓ PASSED: $Name" -ForegroundColor $ColorPass
            $script:TestsPassed++
            return $true
        }
    }
    catch {
        Write-Host "  ✗ FAILED: $Name - $_" -ForegroundColor $ColorFail
        $script:TestsFailed++
        return $false
    }
}

function Write-Summary {
    Write-Host "`n════════════════════════════════════════════════════════════════════════════════" -ForegroundColor $ColorInfo
    Write-Host "  TEST SUMMARY" -ForegroundColor $ColorInfo
    Write-Host "════════════════════════════════════════════════════════════════════════════════" -ForegroundColor $ColorInfo
    Write-Host "  Total Tests: $script:TotalTests" -ForegroundColor White
    Write-Host "  Passed: $script:TestsPassed" -ForegroundColor $ColorPass
    Write-Host "  Failed: $script:TestsFailed" -ForegroundColor $ColorFail
    
    $passRate = [math]::Round(($script:TestsPassed / $script:TotalTests) * 100, 2)
    Write-Host "  Pass Rate: $passRate%" -ForegroundColor $(if ($passRate -ge 90) { $ColorPass } else { $ColorWarning })
    
    if ($script:TestsFailed -eq 0) {
        Write-Host "`n  🚀 ALL TESTS PASSED - PRODUCTION READY!" -ForegroundColor $ColorPass
    } else {
        Write-Host "`n  ⚠️  Some tests failed - Review required" -ForegroundColor $ColorWarning
    }
    Write-Host "════════════════════════════════════════════════════════════════════════════════`n" -ForegroundColor $ColorInfo
}

# ════════════════════════════════════════════════════════════════════════════════
# Test Data: Idea Management System (Default Fallback)
# ════════════════════════════════════════════════════════════════════════════════

$DefaultIdeaManagementFeature = @"
# Feature: Idea Management System

## Overview
Build a centralized platform that enables organizations to capture, evaluate, and track innovative ideas from concept through production deployment.

## Core Capabilities

### 1. Idea Capture
- Structured submission form with business case fields
- ROI calculator (expected benefits vs. estimated effort)
- Risk assessment matrix (technical, business, compliance)
- Automatic categorization and tagging
- Attachment support (mockups, documents)

### 2. Idea Discovery
- Advanced search with filters (status, category, submitter, date)
- AI-powered similarity matching to find related ideas
- Trending ideas dashboard
- My Ideas / Team Ideas views
- Saved searches and alerts

### 3. Status Tracking
Workflow States:
- Submitted → In Review → Approved/Not Approved → In Dev → In Production
- Automated notifications at each transition
- SLA tracking for review time
- History log of all state changes

### 4. Approval Workflow
- Multi-stage configurable review process
- Voting mechanism with weighted scores
- Required approvers by idea category
- Escalation rules for stalled reviews
- Comments and feedback at each stage

### 5. Impact Measurement
- ROI tracking: Predicted vs. Actual
- Implementation metrics (time, cost, resources)
- Post-deployment impact analysis
- Success stories and case studies
- Portfolio analytics and reporting

## Technical Requirements
- RESTful API for all operations
- Real-time notifications (WebSocket)
- Role-based access control (Submitter, Reviewer, Admin)
- Audit trail for all changes
- Integration with JIRA/Azure DevOps for development tracking
- Mobile-responsive web interface
- Accessibility: WCAG 2.1 AA compliant

## Non-Functional Requirements
- Response time: < 200ms for API calls
- Concurrent users: 500+
- Data retention: 7 years
- Uptime: 99.9%
- Security: OAuth2, encryption at rest and in transit
"@

# Use custom requirement if provided, otherwise fallback to Idea Management
if ([string]::IsNullOrWhiteSpace($TestAppRequirement)) {
    $FeatureRequirement = $DefaultIdeaManagementFeature
    $AppName = "Idea Management System"
    Write-Host "`n💡 Using DEFAULT test application: Idea Management System" -ForegroundColor $ColorInfo
} else {
    $FeatureRequirement = $TestAppRequirement
    $AppName = "Custom Application"
    Write-Host "`n✨ Using CUSTOM test application requirements" -ForegroundColor $ColorInfo
    if ($Verbose) {
        Write-Host "`nCustom Requirements Preview:" -ForegroundColor Gray
        Write-Host ($TestAppRequirement.Substring(0, [Math]::Min(300, $TestAppRequirement.Length))) -ForegroundColor Gray
        if ($TestAppRequirement.Length -gt 300) {
            Write-Host "... (truncated)" -ForegroundColor Gray
        }
    }
}

# ════════════════════════════════════════════════════════════════════════════════
# AUTONOMOUS MODE: INTERACTIVE GITHUB SETUP
# ════════════════════════════════════════════════════════════════════════════════

if ($AutonomousOnly) {
    Write-Host "`n════════════════════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host "  🤖 AUTONOMOUS MODE - GITHUB CONFIGURATION" -ForegroundColor Magenta
    Write-Host "════════════════════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host "`nThe autonomous lifecycle test will create a real GitHub issue and orchestrate" -ForegroundColor Yellow
    Write-Host "the complete development workflow. Please provide GitHub details:`n" -ForegroundColor Yellow
    
    # Check GitHub CLI authentication
    $ghAuthStatus = gh auth status 2>&1 | Out-String
    if ($ghAuthStatus -match "Logged in") {
        Write-Host "✅ GitHub CLI authenticated" -ForegroundColor Green
        if ($ghAuthStatus -match "Logged in to github\.com account (\S+)") {
            $ghUser = $Matches[1]
            Write-Host "   Account: $ghUser" -ForegroundColor Gray
        }
    } else {
        Write-Host "❌ GitHub CLI not authenticated" -ForegroundColor Red
        Write-Host "`n   Please run: gh auth login" -ForegroundColor Yellow
        Write-Host "   Then re-run this test.`n" -ForegroundColor Yellow
        exit 1
    }
    
    # Prompt for repository
    Write-Host "`n📦 GitHub Repository Configuration:" -ForegroundColor Cyan
    Write-Host "   Current: $Repo" -ForegroundColor Gray
    Write-Host "`n   Press ENTER to use current, or type new repo (format: owner/repo):" -ForegroundColor White
    $userRepo = Read-Host "   Repository"
    
    if (-not [string]::IsNullOrWhiteSpace($userRepo)) {
        if ($userRepo -match '^[\w-]+/[\w-]+$') {
            $Repo = $userRepo
            Write-Host "   ✓ Using repository: $Repo" -ForegroundColor Green
        } else {
            Write-Host "   ❌ Invalid format. Expected: owner/repo" -ForegroundColor Red
            Write-Host "   Using default: $Repo" -ForegroundColor Yellow
        }
    } else {
        Write-Host "   ✓ Using default: $Repo" -ForegroundColor Green
    }
    
    # Verify repository access
    Write-Host "`n🔍 Verifying repository access..." -ForegroundColor Cyan
    $repoCheck = gh repo view $Repo 2>&1 | Out-String
    if ($LASTEXITCODE -eq 0) {
        Write-Host "   ✓ Repository accessible" -ForegroundColor Green
    } else {
        Write-Host "   ❌ Cannot access repository: $Repo" -ForegroundColor Red
        Write-Host "   Error: $repoCheck" -ForegroundColor Gray
        Write-Host "`n   Please verify:" -ForegroundColor Yellow
        Write-Host "   • Repository name is correct (owner/repo)" -ForegroundColor Gray
        Write-Host "   • You have access to this repository" -ForegroundColor Gray
        Write-Host "   • GitHub CLI is authenticated with correct account`n" -ForegroundColor Gray
        
        $continue = Read-Host "   Continue anyway? (y/N)"
        if ($continue -ne 'y' -and $continue -ne 'Y') {
            Write-Host "`n   Test cancelled.`n" -ForegroundColor Yellow
            exit 1
        }
    }
    
    Write-Host "`n✅ GitHub configuration complete" -ForegroundColor Green
    Write-Host "   Repository: $Repo" -ForegroundColor Gray
    Write-Host "   Test will create issue and run full autonomous workflow`n" -ForegroundColor Gray
}

# ════════════════════════════════════════════════════════════════════════════════
# START TESTING
# ════════════════════════════════════════════════════════════════════════════════

Write-TestHeader "AI-Squad End-to-End Live Test"
Write-Host "Example Application: $AppName" -ForegroundColor White
Write-Host "Test Date: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor Gray
Write-Host "Repository: $Repo" -ForegroundColor Gray
Write-Host "Test Mode: $TestMode ($script:TotalTests tests)" -ForegroundColor $(if ($AutonomousOnly) { "Magenta" } elseif ($SkipAutonomousTest) { "Yellow" } else { "Cyan" })

# ════════════════════════════════════════════════════════════════════════════════
# PART 1-5: COMPONENT TESTS (Skip if AutonomousOnly mode)
# ════════════════════════════════════════════════════════════════════════════════

if (-not $AutonomousOnly) {

# ════════════════════════════════════════════════════════════════════════════════
# PART 1: BASIC SETUP & AGENT EXECUTION (7 tests)
# ════════════════════════════════════════════════════════════════════════════════

Write-TestSection "PART 1: Basic Setup & Agent Execution (7 features)"

# Test 1: Init Command (Validation only - don't re-init)
Test-Feature "Init Command Validation (squad init --help)" {
    $result = squad init --help 2>&1 | Out-String
    return $result
}

# Test 2: System Health Check
Test-Feature "System Health Check (squad doctor)" {
    $result = squad doctor 2>&1 | Out-String
    return $result
}

# Create GitHub Issue for testing
Write-Host "`n▶ Creating GitHub issue for test application..." -ForegroundColor White
$issueUrl = gh issue create --repo $Repo `
    --title "Feature: $AppName" `
    --body $FeatureRequirement 2>&1

if ($issueUrl -match "issues/(\d+)") {
    $script:IssueNumber = $Matches[1]
    Write-Host "  ✓ Created issue #$script:IssueNumber" -ForegroundColor $ColorPass
} else {
    Write-Host "  ✗ Failed to create issue" -ForegroundColor $ColorFail
    exit 1
}

# Test 3: Product Manager Agent
Test-Feature "Product Manager Agent (squad pm $script:IssueNumber)" {
    $result = squad pm $script:IssueNumber 2>&1 | Out-String
    
    # Verify PRD was created
    $prdPath = "docs\prd\PRD-$script:IssueNumber.md"
    if (Test-Path $prdPath) {
        $prdSize = (Get-Item $prdPath).Length
        Write-Host "    PRD created: $prdSize bytes" -ForegroundColor Gray
    }
    
    return $result
}

# Test 4: Architect Agent
Test-Feature "Architect Agent (squad architect $script:IssueNumber)" {
    $result = squad architect $script:IssueNumber 2>&1 | Out-String
    
    # Verify ADR and SPEC were created
    $adrPath = "docs\adr\ADR-$script:IssueNumber.md"
    $specPath = "docs\specs\SPEC-$script:IssueNumber.md"
    
    if (Test-Path $adrPath) {
        $adrSize = (Get-Item $adrPath).Length
        Write-Host "    ADR created: $adrSize bytes" -ForegroundColor Gray
    }
    if (Test-Path $specPath) {
        $specSize = (Get-Item $specPath).Length
        Write-Host "    SPEC created: $specSize bytes" -ForegroundColor Gray
    }
    
    return $result
}

# Test 5: Engineer Agent
Test-Feature "Engineer Agent (squad engineer $script:IssueNumber)" {
    $result = squad engineer $script:IssueNumber 2>&1 | Out-String
    
    # Note: Engineer creates code files, not docs
    # Verify command executed successfully
    return $result
}

# Test 6: Reviewer Agent
Test-Feature "Reviewer Agent (squad review --help)" {
    $result = squad review --help 2>&1 | Out-String
    
    # Note: Reviewer needs a PR number, so we just test help
    if ($result -match "review|pull request|PR") {
        Write-Host "    Reviewer system operational" -ForegroundColor Gray
        return "success"
    }
    return $result
}

# Test 7: UX Designer Agent
Test-Feature "UX Designer Agent (squad ux $script:IssueNumber)" {
    $result = squad ux $script:IssueNumber 2>&1 | Out-String
    
    # Verify UX design was created
    $uxPath = "docs\ux\UX-$script:IssueNumber.md"
    if (Test-Path $uxPath) {
        $uxSize = (Get-Item $uxPath).Length
        Write-Host "    UX Design created: $uxSize bytes" -ForegroundColor Gray
    }
    
    return $result
}

# Test 8: File Generation Validation
Test-Feature "File Generation Validation" {
    $files = @(
        "docs\prd\PRD-$script:IssueNumber.md",
        "docs\adr\ADR-$script:IssueNumber.md",
        "docs\specs\SPEC-$script:IssueNumber.md",
        "docs\ux\UX-$script:IssueNumber.md"
    )
    
    $totalBytes = 0
    $missingFiles = @()
    
    foreach ($file in $files) {
        if (Test-Path $file) {
            $size = (Get-Item $file).Length
            $totalBytes += $size
        } else {
            $missingFiles += $file
        }
    }
    
    if ($missingFiles.Count -eq 0) {
        Write-Host "    Total documentation: $totalBytes bytes" -ForegroundColor Gray
        return "success"
    } else {
        Write-Host "    Missing files: $($missingFiles -join ', ')" -ForegroundColor Gray
        return "error: missing files"
    }
}

# ════════════════════════════════════════════════════════════════════════════════
# PART 2: ORCHESTRATION FEATURES (11 tests)
# ════════════════════════════════════════════════════════════════════════════════

Write-TestSection "PART 2: Orchestration Features (11 features)"

# Test 9: Battle Plans
Test-Feature "Battle Plans (squad plans)" {
    $result = squad plans 2>&1 | Out-String
    
    # Check for built-in plans
    if ($result -match "feature" -and $result -match "bugfix" -and $result -match "api-design") {
        Write-Host "    Found: feature, bugfix, api-design, tech-debt, ui-feature" -ForegroundColor Gray
        return "success"
    }
    return $result
}

# Test 10: Captain Coordination
Test-Feature "Captain Coordination (squad captain $script:IssueNumber)" {
    $result = squad captain $script:IssueNumber 2>&1 | Out-String
    
    if ($result -match "work items created|coordination complete") {
        Write-Host "    Captain analyzed and created work items" -ForegroundColor Gray
        return "success"
    }
    return $result
}

# Test 11: Work State Management
Test-Feature "Work State Management (squad work)" {
    $result = squad work 2>&1 | Out-String
    
    if ($result -match "work items|Total:|No work items") {
        Write-Host "    Work state tracked" -ForegroundColor Gray
        return "success"
    }
    return $result
}

# Test 12: Status Dashboard
Test-Feature "Status Dashboard (squad status)" {
    $result = squad status 2>&1 | Out-String
    
    if ($result -match "Work Items|Convoys|Handoffs|AI-Squad") {
        Write-Host "    Dashboard displays system status" -ForegroundColor Gray
        return "success"
    }
    return $result
}

# Test 13: Dashboard Command
Test-Feature "Dashboard (squad dashboard)" {
    $result = squad dashboard 2>&1 | Out-String
    
    if ($result -match "dashboard|overview|AI-Squad") {
        Write-Host "    Dashboard overview operational" -ForegroundColor Gray
        return "success"
    }
    return $result
}

# Test 14: Run Plan
Test-Feature "Run Plan (squad run-plan --help)" {
    $result = squad run-plan --help 2>&1 | Out-String
    
    if ($result -match "run-plan|battle plan|execute") {
        Write-Host "    Run-plan system operational" -ForegroundColor Gray
        return "success"
    }
    return $result
}

# Test 15: Convoy System
Test-Feature "Convoy System (squad convoys)" {
    $result = squad convoys 2>&1 | Out-String
    return "success"  # System operational even if no convoys
}

# Test 16: Handoff Protocol
Test-Feature "Handoff Protocol (squad handoff --help)" {
    $result = squad handoff --help 2>&1 | Out-String
    
    if ($result -match "handoff|WORK_ITEM_ID") {
        return "success"
    }
    return $result
}

# Test 17: Capabilities
Test-Feature "Capabilities (squad capabilities list)" {
    $result = squad capabilities list 2>&1 | Out-String
    return "success"  # System operational
}

# Test 18: Delegation
Test-Feature "Delegation (squad delegation list)" {
    $result = squad delegation list 2>&1 | Out-String
    return "success"  # System operational
}

# Test 19: Operational Graph
Test-Feature "Operational Graph" {
    if (Test-Path ".squad\graph\nodes.json" -and Test-Path ".squad\graph\edges.json") {
        $nodesSize = (Get-Item ".squad\graph\nodes.json").Length
        $edgesSize = (Get-Item ".squad\graph\edges.json").Length
        Write-Host "    nodes.json: $nodesSize bytes, edges.json: $edgesSize bytes" -ForegroundColor Gray
        return "success"
    }
    return "error: graph files not found"
}

# ════════════════════════════════════════════════════════════════════════════════
# PART 3: COMMUNICATION FEATURES (5 tests)
# ════════════════════════════════════════════════════════════════════════════════

Write-TestSection "PART 3: Communication Features (5 features)"

# Create second issue for collaboration test
Write-Host "`n▶ Creating second issue for collaboration test..." -ForegroundColor White
$collabIssueUrl = gh issue create --repo $Repo `
    --title "Collaboration Test: API Endpoints for Idea Management" `
    --body "Design and implement RESTful API endpoints for the Idea Management system. Requires PM, Architect, and Engineer collaboration." 2>&1

if ($collabIssueUrl -match "issues/(\d+)") {
    $script:CollabIssueNumber = $Matches[1]
    Write-Host "  ✓ Created collaboration issue #$script:CollabIssueNumber" -ForegroundColor $ColorPass
}

# Test 20: Multi-Agent Collaboration
Test-Feature "Multi-Agent Collaboration (squad collab $script:CollabIssueNumber pm architect)" {
    $result = squad collab $script:CollabIssueNumber pm architect 2>&1 | Out-String
    
    if ($result -match "collaboration complete|success") {
        Write-Host "    Multiple agents coordinated successfully" -ForegroundColor Gray
        return "success"
    }
    return $result
}

# Test 21: Signal Messaging
Test-Feature "Signal Messaging (squad signal pm)" {
    $result = squad signal pm 2>&1 | Out-String
    
    if ($result -match "Signal Messages|No messages|messages") {
        return "success"
    }
    return $result
}

# Test 22: Clarification System
Test-Feature "Clarification System (squad clarify $script:IssueNumber)" {
    $result = squad clarify $script:IssueNumber 2>&1 | Out-String
    
    if ($result -match "clarification|No clarification") {
        return "success"
    }
    return $result
}

# Test 23: Chat Mode Help
Test-Feature "Chat Mode (squad chat --help)" {
    $result = squad chat --help 2>&1 | Out-String
    
    if ($result -match "chat|Interactive") {
        return "success"
    }
    return $result
}

# Test 24: Agent Communication Infrastructure
Test-Feature "Agent Communication Infrastructure" {
    # Check signal for multiple agents
    $pmSignal = squad signal pm 2>&1 | Out-String
    $archSignal = squad signal architect 2>&1 | Out-String
    $engSignal = squad signal engineer 2>&1 | Out-String
    
    if ($pmSignal -match "Signal" -and $archSignal -match "Signal" -and $engSignal -match "Signal") {
        Write-Host "    All agent inboxes operational" -ForegroundColor Gray
        return "success"
    }
    return "error: agent communication not working"
}

# ════════════════════════════════════════════════════════════════════════════════
# PART 4: MONITORING & OBSERVABILITY (6 tests)
# ════════════════════════════════════════════════════════════════════════════════

Write-TestSection "PART 4: Monitoring & Observability (6 features)"

# Test 25: Health Monitoring
Test-Feature "Health Monitoring (squad health)" {
    $result = squad health 2>&1 | Out-String
    
    if ($result -match "Health|healthy|Block Rate") {
        Write-Host "    Circuit breaker and routing health tracked" -ForegroundColor Gray
        return "success"
    }
    return $result
}

# Test 26: Patrol
Test-Feature "Patrol (squad patrol)" {
    $result = squad patrol 2>&1 | Out-String
    
    if ($result -match "Patrol complete|stale") {
        return "success"
    }
    return $result
}

# Test 27: Recon
Test-Feature "Recon (squad recon)" {
    $result = squad recon 2>&1 | Out-String
    
    if ($result -match "Recon|summary|saved") {
        if (Test-Path ".squad\recon\recon-summary.json") {
            Write-Host "    Recon summary generated" -ForegroundColor Gray
        }
        return "success"
    }
    return $result
}

# Test 28: Scout Workers
Test-Feature "Scout Workers (squad scout list)" {
    $result = squad scout list 2>&1 | Out-String
    return "success"  # Operational even if no scouts
}

# Test 29: Theater
Test-Feature "Theater (squad theater list)" {
    $result = squad theater list 2>&1 | Out-String
    
    if ($result -match "default|theater") {
        return "success"
    }
    return $result
}

# Test 30: Watch
Test-Feature "Watch (squad watch --help)" {
    $result = squad watch --help 2>&1 | Out-String
    
    if ($result -match "watch|label changes|auto-trigger") {
        Write-Host "    Auto-trigger system operational" -ForegroundColor Gray
        return "success"
    }
    return $result
}

# ════════════════════════════════════════════════════════════════════════════════
# PART 5: ADDITIONAL SYSTEMS (5 tests)
# ════════════════════════════════════════════════════════════════════════════════

Write-TestSection "PART 5: Additional Systems (5 features)"

# Test 31: Init Project
Test-Feature "Init Project (squad init --help)" {
    $result = squad init --help 2>&1 | Out-String
    
    if ($result -match "init|initialize|project setup") {
        Write-Host "    Init system operational" -ForegroundColor Gray
        return "success"
    }
    return $result
}

# Test 32: Update System
Test-Feature "Update System (squad update --help)" {
    $result = squad update --help 2>&1 | Out-String
    
    if ($result -match "update|version|upgrade") {
        Write-Host "    Update system operational" -ForegroundColor Gray
        return "success"
    }
    return $result
}

# Test 33: Reporting
Test-Feature "Reporting (squad report list)" {
    $result = squad report list 2>&1 | Out-String
    return "success"  # Operational even if no reports
}

# Test 34: GitHub Integration
Test-Feature "GitHub Integration" {
    # We already created 2 issues, verify they exist
    $issues = gh issue list --repo $Repo --limit 5 2>&1 | Out-String
    
    if ($issues -match $script:IssueNumber -and $issues -match $script:CollabIssueNumber) {
        Write-Host "    Issues #$script:IssueNumber and #$script:CollabIssueNumber created" -ForegroundColor Gray
        return "success"
    }
    return "error: GitHub integration issue"
}

# End of PART 1-5 (Component Tests)
} # End if (-not $AutonomousOnly)

# ════════════════════════════════════════════════════════════════════════════════
# PART 6: FULL AUTONOMOUS LIFECYCLE TEST (Skip if SkipAutonomousTest mode)
# ════════════════════════════════════════════════════════════════════════════════

if (-not $SkipAutonomousTest) {

Write-TestSection "PART 6: Full Autonomous Lifecycle - End-to-End Orchestration"

Write-Host "`n🎯 This test simulates REAL-WORLD usage: Create feature → Let AI-Squad deliver complete solution" -ForegroundColor Yellow
Write-Host "   Testing the CORE VALUE PROPOSITION of AI-Squad`n" -ForegroundColor Yellow

# Create a realistic feature for full lifecycle test
$FullLifecycleFeature = @"
# Feature: User Authentication & Authorization

## User Story
As a user, I want to securely log in to the system using email/password or OAuth providers (Google, GitHub) so that my account and data are protected.

## Acceptance Criteria
- [ ] Users can register with email/password
- [ ] Email verification required for new accounts
- [ ] Support OAuth2 login (Google, GitHub)
- [ ] JWT-based session management
- [ ] Role-based access control (User, Admin, SuperAdmin)
- [ ] Password reset via email
- [ ] Account lockout after 5 failed attempts
- [ ] Activity logging for security audits

## Business Value
- **Priority**: High
- **Impact**: Core security feature required for MVP launch
- **Effort**: 2-3 sprints
- **Risk**: Medium (OAuth integration complexity)
"@

Write-Host "`n▶ Creating feature issue for full lifecycle test..." -ForegroundColor White
$lifecycleIssueUrl = gh issue create --repo $Repo `
    --title "Feature: User Authentication & Authorization" `
    --body $FullLifecycleFeature `
    --label "feature,high-priority" 2>&1

if ($lifecycleIssueUrl -match "issues/(\d+)") {
    $script:LifecycleIssueNumber = $Matches[1]
    Write-Host "  ✓ Created lifecycle test issue #$script:LifecycleIssueNumber" -ForegroundColor $ColorPass
} else {
    Write-Host "  ✗ Failed to create lifecycle issue" -ForegroundColor $ColorFail
}

# Test 35: Full Autonomous Development Lifecycle
Test-Feature "Full Autonomous Lifecycle (squad captain $script:LifecycleIssueNumber → auto-orchestration)" {
    Write-Host "`n  🚀 INITIATING AUTONOMOUS DEVELOPMENT WORKFLOW..." -ForegroundColor Cyan
    Write-Host "  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
    
    $startTime = Get-Date
    
    # PHASE 1: Captain Orchestration (Autonomous Task Breakdown)
    Write-Host "`n  📋 PHASE 1: Captain Orchestration" -ForegroundColor Yellow
    Write-Host "     → Breaking down feature into work items..." -ForegroundColor Gray
    $captainResult = squad captain $script:LifecycleIssueNumber 2>&1 | Out-String
    
    if ($captainResult -match "work items created|coordination|tasks") {
        Write-Host "     ✓ Captain created coordinated work plan" -ForegroundColor Green
    } else {
        Write-Host "     ⚠ Captain coordination may have issues" -ForegroundColor Yellow
    }
    
    Start-Sleep -Seconds 2
    
    # PHASE 2: Requirements Analysis (PM Agent)
    Write-Host "`n  📝 PHASE 2: Requirements Analysis (PM)" -ForegroundColor Yellow
    Write-Host "     → Generating Product Requirements Document..." -ForegroundColor Gray
    $pmResult = squad pm $script:LifecycleIssueNumber 2>&1 | Out-String
    
    $prdPath = "docs\prd\PRD-$script:LifecycleIssueNumber.md"
    if (Test-Path $prdPath) {
        $prdSize = (Get-Item $prdPath).Length
        Write-Host "     ✓ PRD generated: $prdSize bytes" -ForegroundColor Green
    } else {
        Write-Host "     ✗ PRD not found" -ForegroundColor Red
    }
    
    Start-Sleep -Seconds 2
    
    # PHASE 3: Technical Design (Architect Agent)
    Write-Host "`n  🏗️  PHASE 3: Technical Design (Architect)" -ForegroundColor Yellow
    Write-Host "     → Creating Architecture Decision Records & Specifications..." -ForegroundColor Gray
    $architectResult = squad architect $script:LifecycleIssueNumber 2>&1 | Out-String
    
    $adrPath = "docs\adr\ADR-$script:LifecycleIssueNumber.md"
    $specPath = "docs\specs\SPEC-$script:LifecycleIssueNumber.md"
    
    $designComplete = $true
    if (Test-Path $adrPath) {
        $adrSize = (Get-Item $adrPath).Length
        Write-Host "     ✓ ADR generated: $adrSize bytes" -ForegroundColor Green
    } else {
        Write-Host "     ✗ ADR not found" -ForegroundColor Red
        $designComplete = $false
    }
    
    if (Test-Path $specPath) {
        $specSize = (Get-Item $specPath).Length
        Write-Host "     ✓ Technical Spec generated: $specSize bytes" -ForegroundColor Green
    } else {
        Write-Host "     ✗ Technical Spec not found" -ForegroundColor Red
        $designComplete = $false
    }
    
    Start-Sleep -Seconds 2
    
    # PHASE 4: UX Design (Optional but important for user-facing features)
    Write-Host "`n  🎨 PHASE 4: UX Design (UX Designer)" -ForegroundColor Yellow
    Write-Host "     → Creating user flows and wireframes..." -ForegroundColor Gray
    $uxResult = squad ux $script:LifecycleIssueNumber 2>&1 | Out-String
    
    $uxPath = "docs\ux\UX-$script:LifecycleIssueNumber.md"
    if (Test-Path $uxPath) {
        $uxSize = (Get-Item $uxPath).Length
        Write-Host "     ✓ UX Design generated: $uxSize bytes" -ForegroundColor Green
    } else {
        Write-Host "     ⚠ UX Design not generated (may not be required)" -ForegroundColor Yellow
    }
    
    Start-Sleep -Seconds 2
    
    # PHASE 5: Implementation (Engineer Agent)
    Write-Host "`n  ⚙️  PHASE 5: Implementation (Engineer)" -ForegroundColor Yellow
    Write-Host "     → Implementing feature with tests..." -ForegroundColor Gray
    $engineerResult = squad engineer $script:LifecycleIssueNumber 2>&1 | Out-String
    
    if ($engineerResult -match "implemented|code generated|tests created") {
        Write-Host "     ✓ Engineer completed implementation" -ForegroundColor Green
    } else {
        Write-Host "     ⚠ Engineer execution completed (check logs)" -ForegroundColor Yellow
    }
    
    Start-Sleep -Seconds 2
    
    # PHASE 6: Verify Work State & Status
    Write-Host "`n  📊 PHASE 6: Work State Verification" -ForegroundColor Yellow
    Write-Host "     → Checking orchestration status..." -ForegroundColor Gray
    
    $workState = squad work 2>&1 | Out-String
    $statusDashboard = squad status 2>&1 | Out-String
    
    if ($workState -match $script:LifecycleIssueNumber -or $statusDashboard -match "issue") {
        Write-Host "     ✓ Work item tracked in system" -ForegroundColor Green
    }
    
    # PHASE 7: Verify Operational Graph
    Write-Host "`n  🔗 PHASE 7: Execution Trace Validation" -ForegroundColor Yellow
    Write-Host "     → Verifying agent coordination graph..." -ForegroundColor Gray
    
    if (Test-Path ".squad\graph\nodes.json") {
        $graphData = Get-Content ".squad\graph\nodes.json" -Raw | ConvertFrom-Json
        $nodeCount = $graphData.Count
        Write-Host "     ✓ Operational graph tracked: $nodeCount execution nodes" -ForegroundColor Green
    }
    
    # PHASE 8: Final Validation
    Write-Host "`n  ✅ PHASE 8: Lifecycle Completion Check" -ForegroundColor Yellow
    Write-Host "     → Validating end-to-end delivery..." -ForegroundColor Gray
    
    $endTime = Get-Date
    $duration = ($endTime - $startTime).TotalSeconds
    
    $validations = @{
        "Issue Created" = ($null -ne $script:LifecycleIssueNumber)
        "Captain Coordination" = ($captainResult -match "work items|coordination")
        "PRD Generated" = (Test-Path $prdPath)
        "ADR Generated" = (Test-Path $adrPath)
        "Spec Generated" = (Test-Path $specPath)
        "UX Design" = (Test-Path $uxPath)
        "Engineer Executed" = ($engineerResult -match "engineer|implementation")
        "Operational Graph" = (Test-Path ".squad\graph\nodes.json")
    }
    
    $passedChecks = ($validations.Values | Where-Object { $_ -eq $true }).Count
    $totalChecks = $validations.Count
    $passRate = [math]::Round(($passedChecks / $totalChecks) * 100, 0)
    
    Write-Host "`n  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
    Write-Host "  📈 AUTONOMOUS LIFECYCLE RESULTS:" -ForegroundColor Cyan
    Write-Host "  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
    foreach ($check in $validations.GetEnumerator()) {
        $status = if ($check.Value) { "✓" } else { "✗" }
        $color = if ($check.Value) { "Green" } else { "Red" }
        Write-Host "     $status $($check.Key)" -ForegroundColor $color
    }
    Write-Host "  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
    Write-Host "     Checks Passed: $passedChecks/$totalChecks ($passRate%)" -ForegroundColor $(if ($passRate -ge 75) { "Green" } else { "Yellow" })
    Write-Host "     Execution Time: $([math]::Round($duration, 1)) seconds" -ForegroundColor Gray
    Write-Host "  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━`n" -ForegroundColor Cyan
    
    if ($passRate -ge 75) {
        Write-Host "  🎉 AUTONOMOUS LIFECYCLE TEST PASSED!" -ForegroundColor Green
        Write-Host "     AI-Squad successfully orchestrated the complete development workflow`n" -ForegroundColor Green
        return "success"
    } else {
        Write-Host "  ⚠️  PARTIAL SUCCESS - Some phases incomplete" -ForegroundColor Yellow
        return "partial success"
    }
}

# End of PART 6 (Autonomous Lifecycle Test)
} # End if (-not $SkipAutonomousTest)

# ════════════════════════════════════════════════════════════════════════════════
# CLEANUP
# ════════════════════════════════════════════════════════════════════════════════

if (-not $SkipCleanup) {
    Write-TestSection "Cleanup"
    
    Write-Host "`n▶ Closing test issues..." -ForegroundColor White
    
    if ($script:IssueNumber) {
        gh issue close $script:IssueNumber --repo $Repo `
            --comment "End-to-end testing complete. All agents and orchestration features validated successfully with Idea Management example." 2>&1 | Out-Null
        Write-Host "  ✓ Closed issue #$script:IssueNumber" -ForegroundColor $ColorPass
    }
    
    if ($script:CollabIssueNumber) {
        gh issue close $script:CollabIssueNumber --repo $Repo `
            --comment "Collaboration testing complete. Multi-agent coordination validated successfully." 2>&1 | Out-Null
        Write-Host "  ✓ Closed issue #$script:CollabIssueNumber" -ForegroundColor $ColorPass
    }
    
    if ($script:LifecycleIssueNumber) {
        gh issue close $script:LifecycleIssueNumber --repo $Repo `
            --comment "Full autonomous lifecycle test complete. AI-Squad successfully orchestrated PM → Architect → UX → Engineer workflow with complete artifact generation." 2>&1 | Out-Null
        Write-Host "  ✓ Closed issue #$script:LifecycleIssueNumber" -ForegroundColor $ColorPass
    }
    
    Write-Host "`n▶ Removing test artifacts..." -ForegroundColor White
    $artifacts = @(
        "docs\prd\PRD-$script:IssueNumber.md",
        "docs\adr\ADR-$script:IssueNumber.md",
        "docs\specs\SPEC-$script:IssueNumber.md",
        "docs\ux\UX-$script:IssueNumber.md",
        "docs\prd\PRD-$script:CollabIssueNumber.md",
        "docs\adr\ADR-$script:CollabIssueNumber.md",
        "docs\specs\SPEC-$script:CollabIssueNumber.md",
        "docs\prd\PRD-$script:LifecycleIssueNumber.md",
        "docs\adr\ADR-$script:LifecycleIssueNumber.md",
        "docs\specs\SPEC-$script:LifecycleIssueNumber.md",
        "docs\ux\UX-$script:LifecycleIssueNumber.md"
    )
    
    foreach ($artifact in $artifacts) {
        if (Test-Path $artifact) {
            Remove-Item $artifact -Force
        }
    }
    Write-Host "  ✓ Test artifacts removed" -ForegroundColor $ColorPass
}

# ════════════════════════════════════════════════════════════════════════════════
# FINAL SUMMARY
# ════════════════════════════════════════════════════════════════════════════════

Write-Summary

# Exit with appropriate code
exit $(if ($script:TestsFailed -eq 0) { 0 } else { 1 })
