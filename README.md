# Xequity — Indian Equity Portfolio Maximiser

An AI-powered portfolio analysis tool that acts like a Senior Institutional Equity Strategist with 20+ years of experience in the Indian Capital Markets (NSE/BSE).

## Stack

- **Frontend**: Next.js 14 (App Router), TypeScript, Tailwind CSS, shadcn/ui
- **Backend**: FastAPI (Python), yfinance, pandas-ta
- **AI**: Anthropic Claude API

## Setup

### Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate       # Windows
pip install -r requirements.txt
cp .env.example .env        # Add your ANTHROPIC_API_KEY
uvicorn main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Backend runs on `http://localhost:8000`, Frontend on `http://localhost:3000`.

## Usage

1. Enter your stock holdings (NSE symbols like RELIANCE, TCS, INFY)
2. Set your average buy price and allocation % for each stock
3. Choose your trading style (Swing Trader / Long-term Investor)
4. Optionally add market context or news catalysts
5. Click **Analyze Portfolio** to get a professional-grade analysis

## Analysis Pillars

1. **Technical Setup** — EMA 50/200, RSI, Support/Resistance levels
2. **Fundamental Health** — Quarterly results, margins, debt, PE valuation
3. **Market Sentiment & Flows** — FII/DII activity, corporate actions, news
4. **Macro/Sector Alignment** — Sector rotation phase, economic cycle positioning
