# BillCheck — Logistics Billing Audit SaaS

## Quick Start

```bash
# 1. Clone and navigate
cd logbill

# 2. Start all services
docker-compose up --build

# 3. Open in browser
http://localhost:3000
```

## Services
- **Frontend**: http://localhost:3000 (Next.js 14)
- **Backend API**: http://localhost:8000 (FastAPI)
- **API Docs**: http://localhost:8000/docs

---

## Sample CSV Files for Testing

### Invoice CSV (`invoice_sample.csv`)
```csv
AWB Number,Date,Origin Pincode,Destination Pincode,Weight Billed,Zone,Base Freight,COD Fee,RTO Fee,Fuel Surcharge,Other Surcharges,GST Rate,Total Billed
ABC001,2024-01-15,400001,600001,2.5,ZONE_B,250.00,15.00,0,30.00,0,18,346.70
ABC002,2024-01-15,400001,110001,5.0,ZONE_C,600.00,0,0,72.00,0,18,796.96
ABC003,2024-01-16,400001,600001,1.0,ZONE_B,120.00,8.00,0,14.40,0,18,168.93
ABC001,2024-01-16,400001,600001,2.5,ZONE_B,250.00,15.00,0,30.00,0,18,346.70
ABC004,2024-01-17,400001,500001,3.0,ZONE_D,500.00,0,250.00,60.00,50.00,18,1014.40
ABC005,2024-01-17,400001,380001,2.0,ZONE_A,140.00,0,0,25.00,0,18,195.30
```
*(Note: ABC001 is intentionally duplicated to trigger duplicate_awb check)*

### Contract Rate Card CSV (`contract_sample.csv`)
```csv
Zone,Rate,COD Percentage,RTO Percentage,Fuel Surcharge Percentage,GST Percentage
ZONE_A,60,1.5,50,12,18
ZONE_B,80,1.5,50,12,18
ZONE_C,100,1.5,50,12,18
ZONE_D,120,1.5,50,12,18
LOCAL,40,1.5,50,12,18
```

---

## Billing Checks Performed
1. **Duplicate AWB** — Same AWB billed twice
2. **Weight Overcharge** — Billed weight exceeds contracted rate
3. **Zone Mismatch** — Wrong zone charged for pincode pair
4. **Rate Deviation** — Base freight deviates from contracted rate
5. **COD Fee Mismatch** — COD fee exceeds contracted %
6. **RTO Overcharge** — RTO fee exceeds contracted rate
7. **Fuel Surcharge Mismatch** — Fuel charge exceeds contracted %
8. **Non-Contracted Surcharge** — Surcharge not in contract
9. **GST Miscalculation** — GST doesn't match contracted rate
10. **Arithmetic Total Mismatch** — Row total doesn't add up

## Architecture
```
logbill/
├── backend/          # FastAPI + PostgreSQL
│   └── app/
│       ├── api/      # REST endpoints
│       ├── core/     # DB + config
│       ├── models/   # ORM + schemas
│       └── services/ # Business logic
├── frontend/         # Next.js 14
│   └── app/          # Pages (App Router)
└── docker-compose.yml
```
