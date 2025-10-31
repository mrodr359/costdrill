# Product Requirements Document (PRD) for CostDrill CLI

**Version:** 1.0  
**Date:** October 30, 2025  
**Author:** Grok (based on user discussions)  
**Project Repo:** [To be created by user] – Once you set up the GitHub repo, you can add this PRD as `PRD.md` in the docs folder or root. To download this, copy-paste the content below into a Markdown file (e.g., via VS Code or any text editor) and save it as `PRD.md`. If you want a PDF version, paste it into a Markdown viewer like Dillinger.io and export.

## 1. Executive Summary
CostDrill is an open-source Command-Line Interface (CLI) tool designed to provide interactive, drill-down visibility into cloud costs, starting with AWS. It addresses the pain points of navigating complex cloud billing consoles by offering a Text User Interface (TUI) for selecting services (e.g., EC2), specific resources (e.g., individual instances), or aggregates (e.g., all EC2 in a region), and breaking down costs by components like compute, storage, and data transfer. The tool aims to help developers, DevOps engineers, and FinOps teams identify waste, forecast savings, and automate optimizations.

This PRD outlines the MVP (Minimum Viable Product) scope, with extensibility for multi-cloud support and advanced features.

## 2. Problem Statement
- Cloud costs are opaque and hard to analyze: Users rely on web consoles or scripted queries, which are cumbersome for quick insights.
- Existing tools (e.g., aws-cost-cli, Komiser) lack interactive TUI navigation for per-resource breakdowns.
- Common scenarios: "What's the total cost of this EC2 instance including attached EBS?" or "Aggregate all EC2 costs in us-east-1?" require manual API calls or spreadsheets.
- Wasted spend: Companies lose billions on idle/overprovisioned resources; need easy ways to spot and fix.

## 3. Goals and Objectives
### Business Goals
- Build a viral OSS tool with 1k+ GitHub stars in the first year by solving real DevOps pain.
- Monetization potential: Free core; paid hosted version with multi-account dashboards, AI insights, or enterprise support.
- Community-driven: Encourage contributions for multi-cloud (GCP, Azure) and integrations.

### Product Objectives
- Provide intuitive, terminal-based cost exploration without leaving the CLI.
- Enable quick savings identification (e.g., 10-20% reductions via recommendations).
- Ensure low barrier to entry: Install via pip/Homebrew, minimal setup (AWS credentials).

### Success Metrics
- User adoption: 500+ downloads in first 3 months (track via PyPI stats).
- Engagement: Average session time >5 mins; feedback via GitHub issues.
- Impact: User-reported savings (e.g., surveys or case studies).

## 4. Target Audience
- Primary: DevOps engineers, cloud architects, and individual developers managing AWS environments.
- Secondary: FinOps teams in small-to-medium enterprises; OSS contributors.
- User Personas:
  - **Alex the DevOps Engineer:** Manages multiple AWS accounts; needs fast cost checks during deploys.
  - **Jordan the Freelancer:** Optimizes client costs; wants exportable reports for billing.
  - **Sam the Beginner:** New to AWS; seeks guided navigation without console overload.

## 5. Features
### MVP Features
1. **Interactive TUI Navigation**
   - Dropdown/select for services (e.g., EC2, S3, RDS).
   - For EC2: Select specific instance ID or "All" for aggregation.
   - Region filtering (default: current or specified).
   - Breakdown views: Compute (e.g., On-Demand vs. Spot), Storage (EBS types/volumes), Data Transfer, etc.

2. **Cost Data Fetching and Display**
   - Pull from AWS Cost Explorer API for historical/forecasted costs (daily/monthly granularity).
   - Real-time-ish updates (cache for performance).
   - Terminal tables/charts (using Rich/Textual for visuals).
   - Export: JSON, CSV, or Markdown reports.

3. **Basic Optimizations**
   - Savings recommendations (e.g., "Resize to t3.small for $X savings").
   - "What-if" simulations (e.g., switch instance type).
   - Alerts for cost spikes (threshold-based).

### Future Features (Post-MVP)
- Multi-cloud support (GCP Billing API, Azure Cost Management).
- AI integrations (e.g., natural language queries via local LLMs).
- Automation: Generate Terraform PRs for fixes.
- Sustainability metrics (carbon footprint tied to costs).
- Plugins for Kubernetes (EKS costs) or CI/CD hooks.

## 6. User Stories
As a [user], I want [feature] so that [benefit].

- As a DevOps engineer, I want to launch the TUI and select "EC2" from a dropdown, so I can quickly view costs without typing commands.
- As a DevOps engineer, I want to drill into a specific EC2 instance and see a breakdown (compute + EBS storage), so I can identify if storage is the cost driver.
- As a FinOps user, I want to select "All EC2" in a region and get aggregated costs with forecasts, so I can budget accurately.
- As a beginner, I want exportable reports, so I can share insights with my team.
- As an advanced user, I want CLI flags for non-interactive mode (e.g., `cost-drill ec2 --instance i-123 --output json`), so I can script it.

## 7. Technical Requirements
### Platform and Dependencies
- Language: Python 3.10+ (for broad compatibility).
- Key Libraries:
  - Boto3: AWS SDK for API calls.
  - Textual: TUI framework (dropdowns, tables).
  - Rich: Terminal styling and charts.
  - Pandas: Data processing for aggregations.
- Installation: `pip install cost-drill`; optional Homebrew formula.
- Authentication: Use AWS CLI profiles or env vars (e.g., AWS_ACCESS_KEY_ID).

### Architecture
- Modular: Core engine for API fetches, TUI layer for UI, exporter for outputs.
- Data Flow: User input → API query (Cost Explorer + EC2 describe) → Process/aggregate → Render in TUI.
- Error Handling: Graceful failures (e.g., no permissions → prompt setup).
- Security: No data storage; all local. Comply with AWS terms.

### Non-Functional Requirements
- Performance: <5s response for queries (cache frequent calls).
- Usability: Keyboard-navigable TUI; accessible colors.
- Compatibility: Linux, macOS, Windows (via WSL).
- Testing: Unit tests for API parsers; integration tests for TUI flows.
- Documentation: README with setup, examples; API docs via Sphinx.

## 8. Assumptions and Dependencies
- Users have AWS accounts with Cost Explorer enabled (free tier).
- No initial multi-account support (add via Organizations API later).
- OSS License: MIT for broad adoption.

## 9. Risks and Mitigations
- Risk: AWS API rate limits → Mitigation: Caching and exponential backoff.
- Risk: TUI complexity → Mitigation: Start with basic selects; iterate based on feedback.
- Risk: Low adoption → Mitigation: Promote on Reddit/r/aws, Hacker News; demo video.

## 10. Roadmap
- **Month 1 (MVP):** Core TUI for EC2 costs; basic breakdowns.
- **Month 2:** Add optimizations, exports; beta release on PyPI.
- **Month 3:** Community feedback; multi-service support (S3/RDS).
- **Ongoing:** Multi-cloud, AI features; monetization exploration.

This PRD is a living document—update it in your repo as the project evolves. If you need expansions (e.g., wireframes or code stubs), let me know!