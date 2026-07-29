import concurrent.futures
import time
import requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_URL = "http://localhost:8000"

def test_health():
    try:
        start_time = time.time()
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        duration = time.time() - start_time
        return response.status_code, duration
    except Exception as e:
        return 0, 0

def run_load_test(concurrent_users=50, total_requests=500):
    print(f"Starting load test: {concurrent_users} concurrent users, {total_requests} total requests...")
    success = 0
    failed = 0
    durations = []

    start_time = time.time()
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrent_users) as executor:
        futures = [executor.submit(test_health) for _ in range(total_requests)]
        
        for future in concurrent.futures.as_completed(futures):
            status_code, duration = future.result()
            if status_code == 200:
                success += 1
                durations.append(duration)
            else:
                failed += 1

    total_duration = time.time() - start_time
    
    if durations:
        avg_latency = sum(durations) / len(durations)
        durations.sort()
        p95_latency = durations[int(len(durations) * 0.95)]
    else:
        avg_latency = 0
        p95_latency = 0

    print("--- Load Test Results ---")
    print(f"Total Requests: {total_requests}")
    print(f"Successful: {success}")
    print(f"Failed: {failed}")
    print(f"Total Time: {total_duration:.2f}s")
    print(f"Throughput: {total_requests / total_duration:.2f} req/s")
    print(f"Average Latency: {avg_latency * 1000:.2f} ms")
    print(f"95th Percentile Latency: {p95_latency * 1000:.2f} ms")

if __name__ == "__main__":
    run_load_test()
