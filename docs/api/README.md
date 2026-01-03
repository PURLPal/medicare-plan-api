# API Documentation

Complete documentation for the Medicare Plan API.

## Quick Links

- **[User Guide](user-guide.md)** - How to use the API with examples
- **[API Reference](reference.md)** - Complete endpoint reference
- **[Architecture](architecture.md)** - Technical architecture details

## Example Usage

See the [examples directory](examples/) for:
- [Chrome Extension Integration](examples/chrome-extension.md)
- [Sample ZIP Code Queries](examples/)

## Production Endpoint

**Base URL:** `https://medicare.purlpal-api.com/medicare/`

## Core Endpoints

- `GET /states.json` - List all states
- `GET /zip/{ZIP}.json` - Get plans for ZIP code
- `GET /plan/{PLAN_ID}.json` - Get specific plan details
- `GET /state/{ST}/info.json` - State information

## Filtered Endpoints

- `GET /zip/{ZIP}_MAPD.json` - Medicare Advantage + Drug plans only
- `GET /zip/{ZIP}_MA.json` - Medicare Advantage only
- `GET /zip/{ZIP}_PD.json` - Part D drug plans only

## Coverage

- **51 states** (all 50 states + DC)
- **5,804 plans**
- **39,298 ZIP codes**
- **98.59% coverage**

## Performance

- **Latency:** 290-400ms average
- **Availability:** 100% uptime
- **No rate limits** (use responsibly)
- **CORS enabled** for web applications
