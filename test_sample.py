from typing import List, Dict
from models import SensorData
from collections import defaultdict


def uniform_sample(
    sensor_data: List[SensorData], desired_samples: int
) -> List[SensorData]:
    if not sensor_data:
        return []

    # Calculate the total duration in seconds
    start_time = min(data.timestamp_epoch for data in sensor_data)
    end_time = max(data.timestamp_epoch for data in sensor_data)
    duration_seconds = (end_time - start_time) / 1000  # Convert milliseconds to seconds

    # Calculate samples per second
    total_samples = len(sensor_data)
    samples_per_second = total_samples / duration_seconds

    # Calculate step size
    step = int(total_samples / desired_samples)

    # Select samples uniformly
    sampled_data = [sensor_data[i] for i in range(0, total_samples, step)]

    # Ensure the number of samples matches the requested number
    return sampled_data[:desired_samples]


def sample_by_sensor_type(
    sensor_data: List[SensorData], desired_samples: int
) -> Dict[str, Dict[str, List[SensorData]]]:
    # Group data by device and sensor_type
    grouped_data = defaultdict(lambda: defaultdict(list))
    for data in sensor_data:
        grouped_data[data.device][data.sensor_type].append(data)

    # Apply uniform_sample to each group and store the results
    sampled_data = defaultdict(lambda: defaultdict(list))
    for device, sensors in grouped_data.items():
        for sensor_type, data in sensors.items():
            sampled_data[device][sensor_type] = uniform_sample(data, desired_samples)

    return sampled_data


# Example usage
sensor_data = [
    SensorData(
        id=i,
        device="device1",
        sensor_type=f"type{i % 2}",
        value=i * 0.1,
        timestamp_epoch=i * 100,
        timestamp_millis=i * 100,
        patient_id="patient1",
        encounter_id="encounter1",
    )
    for i in range(100)
]

desired_samples = 2
sampled_data = sample_by_sensor_type(sensor_data, desired_samples)

for device, sensors in sampled_data.items():
    for sensor_type, data in sensors.items():
        print(f"Device: {device}, Sensor Type: {sensor_type}, \nData: {data}")
        print("----------")
