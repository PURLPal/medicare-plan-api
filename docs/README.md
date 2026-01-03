# Documentation Hub

Welcome to the Medicare Plan API documentation!

## Quick Navigation

### 📊 For API Users
Start here if you want to use the Medicare Plan API in your application.

- **[API User Guide](api/user-guide.md)** - Complete guide with examples
- **[API Reference](api/reference.md)** - All endpoints and parameters
- **[API Overview](api/README.md)** - Quick reference
- **[Example Integrations](api/examples/)** - Chrome extensions, sample queries

### 🚀 For Deployment & DevOps
Setting up or maintaining the production infrastructure.

- **[Deployment Guide](deployment/README.md)** - Complete deployment process
- **[Database Setup](deployment/database.md)** - PostgreSQL/RDS setup
- **[Lambda Deployment](deployment/lambda.md)** - AWS Lambda configuration
- **[Migration Notes](deployment/migration.md)** - S3 to database migration

### 🔍 For Data Collection
Scraping Medicare plan data from medicare.gov.

- **[Scraping Overview](scraping/README.md)** - All-states scraping plan
- **[Scraping Guide](scraping/guide.md)** - General scraping instructions
- **[Successful Process](scraping/successful-process.md)** - Proven workflow
- **[State-Specific Guides](scraping/state-guides/)** - Custom state approaches
- **[EC2 Selenium Setup](scraping/ec2-selenium.md)** - Cloud scraping setup

### 💻 For Developers
Contributing to the codebase or developing locally.

- **[Testing Guide](development/testing.md)** - How to test the API
- **[Database Guide](development/database-guide.md)** - Schema and architecture
- **[CONTRIBUTING.md](../CONTRIBUTING.md)** - Contribution guidelines

### 📝 Technical Notes
Important technical decisions and edge cases.

- **[Multi-State ZIPs](notes/multi-state-zips.md)** - How we handle ZIPs that span states
- **[CORS Security](notes/cors-security.md)** - CORS configuration details
- **[County Mapping](notes/county-mapping.md)** - ZIP to county mapping challenges

## Documentation Organization

All documentation is organized by topic:

```
docs/
├── api/                    # API usage documentation
│   ├── README.md          # API overview
│   ├── user-guide.md      # Complete user guide
│   ├── reference.md       # Endpoint reference
│   ├── architecture.md    # Technical architecture
│   └── examples/          # Usage examples
├── deployment/            # Deployment guides
│   ├── README.md          # Deployment overview
│   ├── database.md        # Database deployment
│   ├── lambda.md          # Lambda deployment
│   ├── migration.md       # Migration guide
│   ├── api-deployment.md  # API Gateway setup
│   └── status.md          # Current deployment status
├── scraping/              # Data collection guides
│   ├── README.md          # Scraping overview
│   ├── guide.md           # General scraping guide
│   ├── successful-process.md
│   ├── ec2-selenium.md
│   └── state-guides/      # State-specific guides
├── development/           # Developer guides
│   ├── testing.md         # Testing procedures
│   └── database-guide.md  # Database schema
└── notes/                 # Technical notes
    ├── multi-state-zips.md
    ├── cors-security.md
    └── county-mapping.md
```

## Need Help?

- **New to the project?** → Start with [../README.md](../README.md)
- **Want to contribute?** → See [../CONTRIBUTING.md](../CONTRIBUTING.md)
- **Need directory overview?** → Check [../DIRECTORY_STRUCTURE.md](../DIRECTORY_STRUCTURE.md)
