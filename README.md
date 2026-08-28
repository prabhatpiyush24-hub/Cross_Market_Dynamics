# US & Indian Markets Dashboard

A real-time financial dashboard visualizing the impact of US Markets, Crude Oil, and Commodities on Indian Stock Markets.

## Getting Started

This application has been upgraded to fetch live and historical market data automatically. Because it now uses a backend server to proxy and cache real data, you must have **Node.js** installed on your system to run it.

### 1. Install Node.js
If you haven't already, download and install Node.js from the official website:
[https://nodejs.org/](https://nodejs.org/)

### 2. Install Dependencies
Open your terminal (Command Prompt or PowerShell), navigate to this project's root folder (`d:\US_Indian_Market`), and run:
```bash
npm install
```
This will install `express`, `yahoo-finance2`, `node-cron`, and `cors`.

### 3. Start the Server
Once dependencies are installed, start the local server by running:
```bash
npm start
```
*Note: On the very first start, the server will take a few seconds to securely scrape and cache the historical data from Yahoo Finance.*

### 4. View the Dashboard
Open your web browser and navigate to:
**http://localhost:3000**

## How the Automation Works
- **yahoo-finance2**: We use this powerful library to fetch data (NIFTY 50, S&P 500, Crude Oil, USD/INR) directly from Yahoo Finance without needing a paid API key.
- **Local Caching (`data.json`)**: To prevent hitting rate limits and ensure lightning-fast load times, the backend caches the fetched data locally in a `data.json` file.
- **Daily Cron Job**: A background worker (`node-cron`) automatically triggers at Midnight every day to fetch the newest market closes and update the `data.json` cache seamlessly.
