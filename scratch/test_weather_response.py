import asyncio
import httpx
import json

ak = "pcwYdWdoOhqYZI8w1IvUTmxNcnXfUbG7"
url = "https://api.map.baidu.com/weather/v1/"
params = {
    "district_id": "110100",  # Beijing
    "data_type": "all",
    "ak": ak
}

async def main():
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url, params=params)
        print("Status code:", resp.status_code)
        data = resp.json()
        print("Response Keys:", list(data.keys()))
        if "result" in data:
            result = data["result"]
            print("Result Keys:", list(result.keys()))
            if "forecast_hours" in result:
                print("\nForecast Hours sample (first 2 items):")
                print(json.dumps(result["forecast_hours"][:2], indent=2, ensure_ascii=False))
            else:
                print("\nNo forecast_hours found in result!")
            if "forecasts" in result:
                print("\nForecasts sample (first 2 items):")
                print(json.dumps(result["forecasts"][:2], indent=2, ensure_ascii=False))
            else:
                print("\nNo forecasts found in result!")
        else:
            print("Error data:", data)

if __name__ == "__main__":
    asyncio.run(main())
