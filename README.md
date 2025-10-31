# CostDrill

> Interactive CLI tool for AWS cost exploration with drill-down visibility

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

CostDrill is an open-source Command-Line Interface (CLI) tool that provides interactive, drill-down visibility into AWS cloud costs. Navigate your cloud billing with a beautiful Text User Interface (TUI) without leaving your terminal.

## Features

- **Interactive TUI Navigation**: Browse AWS services, select specific resources, and drill down into cost breakdowns
- **Service Support**: EC2, S3, RDS, and more (starting with EC2 in MVP)
- **Cost Breakdowns**: View costs by compute, storage, data transfer, and other components
- **Region Filtering**: Focus on specific regions or view all at once
- **Export Reports**: Generate JSON, CSV, or Markdown reports
- **Optimization Recommendations**: Get savings suggestions and what-if simulations
- **Real-time Updates**: Cached data for quick responses

## Installation

### Prerequisites

- Python 3.10 or higher
- AWS account with Cost Explorer enabled
- AWS credentials configured (via AWS CLI or environment variables)

### Install from PyPI (Coming Soon)

```bash
pip install costdrill
```

### Install from Source

```bash
git clone https://github.com/mrodr359/costdrill.git
cd costdrill
pip install -e .
```

## Quick Start

### 1. Configure AWS Credentials

Ensure your AWS credentials are configured. You can use the AWS CLI:

```bash
aws configure
```

Or set environment variables:

```bash
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
export AWS_DEFAULT_REGION=us-east-1
```

### 2. Launch CostDrill

```bash
costdrill
```

### 3. Navigate the TUI

- Use arrow keys to navigate
- Press Enter to select
- Press 'q' to quit

## Usage Examples

### Interactive Mode

```bash
# Launch the interactive TUI
costdrill

# Start with a specific service
costdrill --service ec2

# Focus on a specific region
costdrill --region us-west-2
```

### Command-Line Mode

```bash
# Get costs for a specific EC2 instance
costdrill ec2 --instance i-1234567890abcdef0 --output json

# Aggregate all EC2 costs in a region
costdrill ec2 --region us-east-1 --aggregate

# Export report
costdrill ec2 --export costs_report.csv
```

## Architecture

CostDrill follows a modular architecture:

```
costdrill/
├── core/       # AWS API interactions and data fetching
├── tui/        # Textual-based user interface components
├── exporters/  # Report generation (JSON, CSV, Markdown)
└── utils/      # Helper functions and utilities
```

## Development

### Setup Development Environment

```bash
# Clone the repository
git clone https://github.com/mrodr359/costdrill.git
cd costdrill

# Install with development dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Format code
black .

# Lint code
ruff check .

# Type check
mypy costdrill
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=costdrill --cov-report=html
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request. For major changes, please open an issue first to discuss what you would like to change.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Roadmap

- [x] MVP: Interactive TUI for EC2 cost exploration
- [ ] Add S3, RDS, and other service support
- [ ] Multi-account support via AWS Organizations
- [ ] AI-powered cost optimization suggestions
- [ ] Multi-cloud support (GCP, Azure)
- [ ] Terraform/IaC integration for automated fixes

See the [PRD](PRD.md) for detailed feature planning.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Built with [Textual](https://textual.textualize.io/) for the TUI
- AWS SDK via [Boto3](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html)
- Terminal styling with [Rich](https://rich.readthedocs.io/)

## Support

- [GitHub Issues](https://github.com/mrodr359/costdrill/issues)
- [Documentation](https://github.com/mrodr359/costdrill/docs)

---

Made with ❤️ for the DevOps and FinOps community
