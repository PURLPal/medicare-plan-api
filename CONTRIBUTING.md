# Contributing to Medicare Plan API

Thank you for your interest in contributing to the Medicare Plan API project!

## Project Structure

```
medicare-plan-api/
├── docs/                   # All documentation
│   ├── api/               # API documentation
│   ├── deployment/        # Deployment guides
│   ├── scraping/          # Scraping documentation
│   ├── development/       # Development guides
│   └── notes/             # Technical notes
├── src/                   # Source code
│   ├── scrapers/         # Web scraping scripts
│   ├── builders/         # API/data builders
│   ├── api/              # API server code
│   ├── deploy/           # Deployment scripts
│   └── utils/            # Utility functions
├── tests/                 # Test files
├── scripts/               # Utility scripts
├── lambda/                # AWS Lambda deployment
├── database/              # Database scripts
├── data/                  # Data files
├── config/                # Configuration files
└── archive/               # Deprecated files
```

## Getting Started

### Prerequisites

- Python 3.11+
- PostgreSQL 15.8+ (for database work)
- AWS CLI configured (for deployment)
- Virtual environment recommended

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd medicare_overview_test

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt  # If available
```

## Development Workflow

### 1. Scraping New Data

To scrape Medicare plan data for a state:

```bash
# Use state-specific scrapers in src/scrapers/state_scrapers/
python3 src/scrapers/state_scrapers/scrape_<state>.py
```

See [docs/scraping/guide.md](docs/scraping/guide.md) for detailed instructions.

### 2. Building API Files

After scraping data:

```bash
# Build static API files
python3 src/builders/build_static_api.py

# Or build for specific states
python3 src/builders/build_all_state_apis.py
```

### 3. Testing

Run tests before committing:

```bash
# Test API endpoints
./tests/test_medicare_api.sh

# Test comprehensive coverage
python3 tests/test_api_comprehensive.py

# Test specific states
python3 tests/test_all_states_live.py
```

See [docs/development/testing.md](docs/development/testing.md) for more details.

### 4. Deploying

For database updates:

```bash
# Load new data into database
python3 database/load_data_fast.py "host=... dbname=... user=... password=..."
```

For Lambda updates:

```bash
# Deploy updated Lambda function
./src/deploy/deploy_medicare_api.sh
```

See [docs/deployment/README.md](docs/deployment/README.md) for complete deployment guide.

## Code Style

### Python

- Follow PEP 8 style guide
- Use meaningful variable names
- Add docstrings to functions
- Keep functions focused and single-purpose

### File Organization

- **Scrapers** go in `src/scrapers/state_scrapers/`
- **Parsers** go in `src/scrapers/parsers/`
- **Builders** go in `src/builders/`
- **Tests** go in `tests/`
- **Documentation** goes in appropriate `docs/` subdirectory

## Adding New States

To add Medicare plan data for a new state:

1. **Create scraper**: `src/scrapers/state_scrapers/scrape_<state>.py`
2. **Create parser** (if needed): `src/scrapers/parsers/<state>_parser.py`
3. **Test scraping**: Verify data quality
4. **Update database**: Load scraped data
5. **Document**: Add state guide to `docs/scraping/state-guides/<state>.md`

## Testing Guidelines

### Before Committing

- Run API tests: `./tests/test_medicare_api.sh`
- Verify data quality
- Check for errors in logs

### Test Coverage

- Test all three plan categories (MAPD, MA, PD)
- Test multi-county ZIPs
- Test category filtering endpoints
- Verify response times

## Documentation

### When to Update Documentation

- Adding new features
- Changing API endpoints
- Modifying deployment process
- Adding new scrapers

### Documentation Structure

- **API docs**: User-facing API documentation
- **Deployment docs**: DevOps and deployment guides
- **Scraping docs**: Data collection processes
- **Development docs**: Internal development guides
- **Notes**: Technical notes and decisions

## Commit Messages

Use clear, descriptive commit messages:

```
Good: "Add scraper for Vermont Medicare plans"
Good: "Fix duplicate county records in database"
Bad: "Update files"
Bad: "Fix bug"
```

## Pull Request Process

1. Create a feature branch
2. Make your changes
3. Test thoroughly
4. Update documentation
5. Submit pull request with clear description
6. Address review comments

## Questions?

- **API Usage**: See [docs/api/user-guide.md](docs/api/user-guide.md)
- **Testing**: See [docs/development/testing.md](docs/development/testing.md)
- **Deployment**: See [docs/deployment/README.md](docs/deployment/README.md)
- **Scraping**: See [docs/scraping/guide.md](docs/scraping/guide.md)

## License

Public domain - Medicare plan data is publicly available from Medicare.gov.
