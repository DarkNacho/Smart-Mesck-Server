import os
from typing import Annotated
import httpx
from fastapi import Depends, HTTPException
from sqlalchemy import func
from sqlmodel import Session
from sqlalchemy.orm import aliased
from database import get_session
from models import User


HAPI_FHIR_URL = os.getenv("HAPI_FHIR_URL")

db_dependency = Annotated[Session, Depends(get_session)]


async def fetch_resource(resource_type: str, resource_id: str, token: str) -> dict:
    """
    Fetch a resource from the HAPI FHIR server.

    Args:
        resource_type (str): The type of the resource (e.g., "Patient").
        resource_id (str): The ID of the resource.
        token (str): Authorization token.

    Returns:
        dict: The fetched resource.

    Raises:
        HTTPException: If the resource cannot be fetched.
    """
    if not HAPI_FHIR_URL:
        raise HTTPException(status_code=500, detail="HAPI_FHIR_URL is not configured")

    url = f"{HAPI_FHIR_URL}/{resource_type}/{resource_id}"
    headers = {"Authorization": f"Bearer {token}"}

    print(f"Fetching {url}")

    async with httpx.AsyncClient(timeout=50.0) as client:
        response = await client.get(url, headers=headers)

    if response.status_code != 200:
        response_data = response.json()
        diagnostic_message = "Failed to fetch {url}\n"
        diagnostic_message += response_data.get("issue", [{}])[0].get(
            "diagnostics", "Unknown error"
        )
        raise HTTPException(status_code=response.status_code, detail=diagnostic_message)

    return response.json()


async def fetch_resources(
    resource_type: str,
    params: dict,
    token: str,
) -> dict:
    """
    Fetch a resource from the HAPI FHIR server.

    Args:
        resource_type (str): The type of the resource (e.g., "Patient").
        resource_id (str): The ID of the resource.
        token (str): Authorization token.

    Returns:
        dict: The fetched resource.

    Raises:
        HTTPException: If the resource cannot be fetched.
    """
    if not HAPI_FHIR_URL:
        raise HTTPException(status_code=500, detail="HAPI_FHIR_URL is not configured")

    url = f"{HAPI_FHIR_URL}/{resource_type}"
    headers = {"Authorization": f"Bearer {token}"}

    print(f"Fetching {url} with params: {params}")

    async with httpx.AsyncClient(timeout=50.0, params=params) as client:
        response = await client.get(url, headers=headers)

    if response.status_code != 200:
        response_data = response.json()
        diagnostic_message = f"Failed to fetch {url}\n"
        diagnostic_message += response_data.get("issue", [{}])[0].get(
            "diagnostics", "Unknown error"
        )
        raise HTTPException(status_code=response.status_code, detail=diagnostic_message)

    return response.json()


async def create_resource(resource_type: str, resource_data: dict, token: str) -> dict:
    """
    Create a new resource on the HAPI FHIR server.

    Args:
        resource_type (str): The type of the resource to create (e.g., "Patient", "Observation").
        resource_data (dict): The JSON representation of the FHIR resource to create.
        token (str): Authorization token.

    Returns:
        dict: The created resource as returned by the server, including assigned ID.

    Raises:
        HTTPException: If the resource cannot be created.
    """
    if not HAPI_FHIR_URL:
        raise HTTPException(status_code=500, detail="HAPI_FHIR_URL is not configured")

    url = f"{HAPI_FHIR_URL}/{resource_type}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/fhir+json",
    }

    print(f"Creating {resource_type} at {url}")

    try:
        async with httpx.AsyncClient(timeout=50.0) as client:
            response = await client.post(url, headers=headers, json=resource_data)

        if response.status_code not in [200, 201]:
            response_data = response.json()
            diagnostic_message = f"Failed to create {resource_type} resource\n"
            diagnostic_message += response_data.get("issue", [{}])[0].get(
                "diagnostics", "Unknown error"
            )
            raise HTTPException(
                status_code=response.status_code, detail=diagnostic_message
            )

        return response.json()
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=500, detail=f"Error communicating with FHIR server: {str(e)}"
        )


async def update_resource(
    resource_type: str, resource_id: str, resource_data: dict, token: str
) -> dict:
    """
    Update an existing resource on the HAPI FHIR server.

    Args:
        resource_type (str): The type of the resource to update (e.g., "Patient").
        resource_id (str): The ID of the resource to update.
        resource_data (dict): The updated JSON representation of the FHIR resource.
        token (str): Authorization token.

    Returns:
        dict: The updated resource as returned by the server.

    Raises:
        HTTPException: If the resource cannot be updated.
    """
    if not HAPI_FHIR_URL:
        raise HTTPException(status_code=500, detail="HAPI_FHIR_URL is not configured")

    url = f"{HAPI_FHIR_URL}/{resource_type}/{resource_id}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/fhir+json",
    }

    print(f"Updating {resource_type}/{resource_id} at {url}")

    try:
        async with httpx.AsyncClient(timeout=50.0) as client:
            response = await client.put(url, headers=headers, json=resource_data)

        if response.status_code not in [200, 201]:
            response_data = response.json()
            diagnostic_message = f"Failed to update {resource_type}/{resource_id}\n"
            diagnostic_message += response_data.get("issue", [{}])[0].get(
                "diagnostics", "Unknown error"
            )
            raise HTTPException(
                status_code=response.status_code, detail=diagnostic_message
            )

        return response.json()
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=500, detail=f"Error communicating with FHIR server: {str(e)}"
        )


async def delete_resource(resource_type: str, resource_id: str, token: str) -> dict:
    """
    Delete a resource from the HAPI FHIR server.

    Args:
        resource_type (str): The type of the resource to delete (e.g., "Patient").
        resource_id (str): The ID of the resource to delete.
        token (str): Authorization token.

    Returns:
        dict: The server response to the deletion request.

    Raises:
        HTTPException: If the resource cannot be deleted.
    """
    if not HAPI_FHIR_URL:
        raise HTTPException(status_code=500, detail="HAPI_FHIR_URL is not configured")

    url = f"{HAPI_FHIR_URL}/{resource_type}/{resource_id}"
    headers = {"Authorization": f"Bearer {token}"}

    print(f"Deleting {resource_type}/{resource_id}")

    try:
        async with httpx.AsyncClient(timeout=50.0) as client:
            response = await client.delete(url, headers=headers)

        if response.status_code not in [200, 204]:
            response_data = response.json()
            diagnostic_message = f"Failed to delete {resource_type}/{resource_id}\n"
            diagnostic_message += response_data.get("issue", [{}])[0].get(
                "diagnostics", "Unknown error"
            )
            raise HTTPException(
                status_code=response.status_code, detail=diagnostic_message
            )

        # For successful deletion, return a simple response
        if response.status_code == 204:  # No content
            return {
                "status": "success",
                "message": f"{resource_type}/{resource_id} successfully deleted",
            }

        return response.json()
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=500, detail=f"Error communicating with FHIR server: {str(e)}"
        )


def parse_patient_info(patient):
    # Initialize an empty dictionary to hold the parsed information
    parsed_info = {}

    # Extract and add basic information
    parsed_info["ID"] = patient.get("id", "N/A")

    identifier = patient.get("identifier", [])
    for iden in identifier:
        if iden["system"] == "RUT":
            parsed_info["RUT"] = iden.get("value", "N/A")
    parsed_info["Name"] = " ".join(
        patient.get("name", [{}])[0].get("given", [])
        + [patient.get("name", [{}])[0].get("family", "")]
    )
    parsed_info["Gender"] = patient.get("gender", "N/A")
    parsed_info["BirthDate"] = patient.get("birthDate", "N/A")

    # Extract and add contact information
    telecoms = patient.get("telecom", [])
    for telecom in telecoms:
        if telecom["system"] == "phone":
            parsed_info["Phone"] = telecom.get("value", "N/A")
        elif telecom["system"] == "email":
            parsed_info["Email"] = telecom.get("value", "N/A")

    # Extract and add marital status
    marital_status = (
        patient.get("maritalStatus", {}).get("coding", [{}])[0].get("display", "N/A")
    )
    parsed_info["Marital Status"] = marital_status

    # Extract and add general practitioner information
    practitioners = patient.get("generalPractitioner", [])
    parsed_info["General Practitioners"] = [
        practitioner.get("reference", "N/A") for practitioner in practitioners
    ]

    return parsed_info


def get_fhir_id(
    rut: str,
    db: db_dependency,
):
    """
    Retrieves a user's FHIR ID given their RUT.
    This endpoint allows obtaining the FHIR ID without needing full authentication.
    """
    user = db.query(User).filter(User.rut == rut).first()

    if not user:
        return {"error": "User not found"}

    return {"fhir_id": user.fhir_id}
