from datetime import datetime
import random
from sqlmodel import SQLModel, create_engine
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()


DB_URL = os.getenv("DB_URL")
# DB_FILE = "sqlite:///database.db"
engine = create_engine(DB_URL, echo=True)


def create_database():
    SQLModel.metadata.create_all(engine)


def get_session():
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def populate_db():
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    bcrypt_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    user_nacho = User(
        email="dark_nacho_xd@hotmail.cl",
        fhir_id="1",
        phone_number="+56964073739",
        name="Ignacio Martínez",
        rut="198625388",
        validate=True,
        hash_password=bcrypt_context.hash("nacho1234"),
        role="Practitioner",
    )

    session.add(user_nacho)
    #session.add(user_admin)
    # session.add(user_practitioner)
    # session.add(user_patient)

    session.commit()


def generate_random_data():
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db_session = SessionLocal()

    patients = ["patient_1", "patient_2"]
    sensor_types = [
        "oxygen_saturation",
        "heart_rate",
        "acceleration_x",
        "acceleration_y",
        "acceleration_z",
        "angular_velocity_x",
        "angular_velocity_y",
        "angular_velocity_z",
    ]
    sample_counts = {
        "oxygen_saturation": 100,
        "heart_rate": 100,
        "acceleration_x": 200,
        "acceleration_y": 200,
        "acceleration_z": 200,
        "angular_velocity_x": 150,
        "angular_velocity_y": 150,
        "angular_velocity_z": 150,
    }  # Diferentes cantidades de muestras para cada sensor
    number_of_encounters = 3  # Definir el número de encuentros

    for patient in patients:
        for encounter_index in range(
            number_of_encounters
        ):  # Iterar sobre cada encuentro
            encounter_id = f"encounter_{encounter_index}_{patient}"
            for sensor_type in sensor_types:
                for n in range(sample_counts[sensor_type]):
                    time = datetime.now().timestamp() + (n + 1) * 10
                    if sensor_type == "oxygen_saturation":
                        value = random.uniform(95, 100)  # Saturación de oxígeno
                    elif sensor_type == "heart_rate":
                        value = random.randint(60, 100)  # Frecuencia cardíaca
                    elif "acceleration" in sensor_type:
                        value = random.uniform(-1, 1)  # Aceleración en x, y, z
                    elif "angular_velocity" in sensor_type:
                        value = random.uniform(
                            -180, 180
                        )  # Velocidad angular en x, y, z
                    else:
                        value = 0  # Valor por defecto

                    data = SensorData(
                        device="device_1",
                        sensor_type=sensor_type,
                        value=value,
                        timestamp_epoch=int(time),
                        timestamp_millis=int(time * 1000),
                        patient_id=patient,
                        encounter_id=encounter_id,
                    )
                    db_session.add(data)
            db_session.commit()


if __name__ == "__main__":
    from models import User, SensorData
    from passlib.context import CryptContext

    # if os.path.exists(DB_FILE):
    #    os.remove(DB_FILE)
    #create_database()
    #generate_random_data()
    populate_db()
