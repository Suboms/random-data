import hashlib
import json

import faker_commerce
from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiParameter,
    OpenApiResponse,
    OpenApiTypes,
    extend_schema,
)

# from drf_spectacular.types import
from faker import Faker
from rest_framework import status
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.renderers import BrowsableAPIRenderer, JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from commons.renderer import CsvRenderer, ExcelRenderer, PdfRenderer
from commons.throttles import (
    AnonUserRateThrottle,
    FreeUserRateThrottle,
    PaidUserRateThrottle,
)
from helpers.data_generator import DataGenerator
from helpers.unique_id import device_id


@extend_schema(
    description="""
This API endpoint provides a flexible way to generate randomized mock data based on the specified **Type** query parameter. Users can specify data types such as **Person**, **Product**, or **Weather** to receive randomized entries that simulate real-world data for testing or development purposes.

\nThe endpoint supports customizable data generation limits (via the optional **Range** parameter) and various response formats parameter including **JSON**, **CSV**, **PDF**, and **xlsx**, depending on the client's requested content type. Additionally, an optional **Seed** parameter allows for consistent, repeatable data generation, ensuring that requests with the same seed produce identical outputs.
\nAccess control and data limits are determined by user authentication status. Unauthenticated users are throttled with limited data access while authenticated users receive increased limits with optional seed values for consistency across requests, and paid users get the highest data range.

# Data Generation Logic
This API leverages the `Faker` library to generate realistic data for multiple domains, including personal profiles, e-commerce products, and weather conditions. The data generation is controlled by the `DummyData` view class, which dynamically maps query parameters to specific methods in the `DataGenerator` class. These methods handle the creation of structured and diverse datasets.

The `DummyData` class contains a dictionary, `faker_methods`, which maps query parameter values (e.g.`person`, `product`, `weather`) to their respective data generation methods in `DataGenerator`. This mapping ensures that the correct method is called based on the client's request.

For example, if the query parameter `type=person` is provided, the API will invoke the `generate_person_data` method to produce records with fields like name, age, gender, and email.

# Custom Providers
The API extends the functionality of the `Faker` library by incorporating a custom provider from the `faker_commerce` module. This provider enhances the library's capabilities, enabling the generation of e-commerce-related data such as product names, categories, and SKU identifiers.

# Key Features of the DataGenerator Class
The `DataGenerator` class contains reusable methods for generating specific types of data:

1. Personal Data: The `generate_person_data` method creates detailed profiles, including name, age, gender, nationality, phone number, address, and email. The email addresses are consistently generated using a predefined Gmail domain for simplicity.

2. Weather Data: The `generate_weather_data` method simulates weather conditions, including temperature, humidity, wind speed, and general weather conditions (e.g., "Sunny", "Rainy"). It also includes location details such as city and country.

3. Product Data: The `generate_product_data` method generates e-commerce data, including product names, categories, prices (formatted as currency), stock levels, and unique SKUs.

4. Phone Number Generation: A utility method, `generate_phone_num`, creates realistic phone numbers by combining country calling codes with randomly generated digits.

# Data Seeding for Reproducibility
To ensure consistent results across requests, the API uses a seeding mechanism with the `Faker` library. This mechanism ensures that the same input produces identical output, allowing users to generate reproducible datasets.

For authenticated users, especially paid users, the `seed` is a combination of the user's unique ID and an optional seed parameter provided in the request. This combined seed value is hashed to create a deterministic, user-specific seed. The reason for combining and hashing the seed is to ensure that if two different authenticated users pass the same seed parameter, the generated data will remain consistent for each individual user but differ between users. This design ensures both reproducibility and uniqueness across users.

For unauthenticated users, a default seed value is assigned based on the device ID. The device ID is itself a hashed combination of the browser's user agent, the user's IP address, and a randomly generated UUID4 value. This approach ensures that data generated for unauthenticated requests is unique to the device but remains random for each session, accommodating various user scenarios.

# Error Handling and Validation
The API includes robust input validation to ensure correct usage:

- If the `type` query parameter is missing, an error is returned indicating that the parameter is required.
- If an unsupported `type` is provided, an error message informs the client about the invalid data type.
This validation ensures that clients receive clear feedback about their requests and reduces the likelihood of misuse.

# Response Structure
The API groups the generated data into a JSON object where each key corresponds to a requested data type, and its value is a list of generated records. For example, a request with `type=person` will return a JSON object containing a `person` key with an array of generated personal data.

Depending on the `Accept` header in the client's request, the API can return data in various formats:
- JSON (default).
- CSV, Excel, or PDF, with appropriate file names and formats for download.

# File Naming Conventions 
The file format and structure of the response will depend on the `format` quer parameter and will follow thes conventions.
- JSON Format (Default)
  - The response is returned as a JSON object. The filename is simply `data.json`

- CSV Format
  - When the `format` query parameter is set to `csv`, the response will be returned as a `.zip` file containing seperate CSV files for each type requestd. 

  - File Naming Covention: The zip file will be named `data_csv.zip`. Inside the zip file, each type will have its own CSV file named `<type.csv>`. For example if both `product` and `person` type are requested, the zip file will contain:

    - data_csv.zip
      - person.csv
      - prduct.csv 

- Excel Format
  - When the `format` query parameter is set to `xlsx`, the response will be returned as an excel workbook with each requested type placed in a seperated sheet within the workbook.

  - File Naming Convention: The excel workbook will be named `data.xlsx`. Within the workbook, each sheet will be named after each type requested. For example, if `person` and `product` types are requested, the Excel file will have two sheets:

    - data.xlsx
      - Sheet 1: `person`
      - Sheet 2: `product`

- PDF Format:
  - When the format query parameter is set to pdf, the response will be returned as a single PDF file containing all the requested data types in a formatted layout.
  - File Naming Convention: The PDF file will be named data.pdf

# Extensibility
This API is designed to be easily extendable. New data types can be added by implementing additional methods in the `DataGenerator` class and mapping them to query parameters in the `faker_methods` dictionary. For instance, adding a `vehicle` data type would involve creating a `generate_vehicle_data` method and updating the mapping to include `"vehicle": self.generate_vehicle_data`.
""",
    summary="This API endpoint provides a flexible way to generate randomized mock data based on the specified Type query parameter",
    # responses={200: OpenApiTypes.OBJECT},
    parameters=[
        OpenApiParameter(
            name="type",
            type=str,
            location=OpenApiParameter.QUERY,
            required=True,
            many=True,
            description=(
                "Specifies the type(s) of data to generate. "
                "_Available Values_: `person`, `product`, `weather`. "
                "Accepts multiple values, e.g., `type=person&type=product`."
            ),
        ),
        OpenApiParameter(
            name="format",
            type=str,
            location=OpenApiParameter.QUERY,
            required=False,
            description=(
                "Specifies the response format. Defaults to `json`. "
                "_Available Values_: `json`, `csv`, `pdf`, `excel`."
            ),
        ),
        OpenApiParameter(
            name="range",
            type=int,
            location=OpenApiParameter.QUERY,
            required=False,
            description=(
                "Specifies the number of records to generate. Defaults to `50`. "
                "The maximum value is determined by the user's throttling rate."
            ),
        ),
        OpenApiParameter(
            name="seed",
            type=str,
            location=OpenApiParameter.QUERY,
            required=False,
            description=(
                "\nProvides a seed value for consistent random data generation. "
                "If omitted, random seeding is applied. "
                "Authenticated users with this parameter receive consistent results. (`For paid users only`)"
            ),
        ),
    ],
    responses={
        200: OpenApiResponse(
            response=OpenApiTypes.OBJECT,
            description="Returns an object named 'data' containing a nested object or list of objects that match the specified query parameters. The data structure of 'data' may vary based on the query parameters provided.",
            examples=[
                OpenApiExample(
                    name="200 Response",
                    value=json.loads(
                        """{"data": {"person": [{"name": "Isaac Li", "age": 77, "gender": "Female", "nationality": "United Arab Emirates", "phone_number": "+2589346606542", "address": "PSC 2500, Box 4033 APO AA 10639", "email": "woodrichard@gmail.com"}, {"name": "Danielle Anderson", "age": 54, "gender": "Male", "nationality": "Gibraltar", "phone_number": "+2291546515334", "address": "387 Ruth Square Davischester, SC 09956", "email": "nashley@gmail.com"}]}}"""
                    ),
                    response_only=True,
                )
            ],
        ),
        400: OpenApiResponse(
            response=OpenApiTypes.OBJECT,
            description="Returns an error if the required 'type' query parameter is missing or if an unsupported type is specified in the query.",
            examples=[
                OpenApiExample(
                    name="Missing Type Parameter",
                    value={"error": "Query parameter 'type' is required."},
                ),
                OpenApiExample(
                    name="Unsupported Type",
                    value={"error": 'Data type "{type}" is not supported.'},
                ),
            ],
        ),
    },
)
class DummyData(APIView, DataGenerator):

    fake = Faker()
    fake.add_provider(faker_commerce.Provider)
    permission_classes = [IsAuthenticatedOrReadOnly]
    authentication_classes = [JWTAuthentication]
    renderer_classes = [
        JSONRenderer,
        BrowsableAPIRenderer,
        ExcelRenderer,
        PdfRenderer,
        CsvRenderer,
    ]

    def get_throttles(self):
        if not self.request.user.is_authenticated:
            return [AnonUserRateThrottle()]
        elif self.request.user.is_paiduser:
            return [PaidUserRateThrottle()]
        return [FreeUserRateThrottle()]

    def get(self, request):
        # Mapping of query parameter values to Faker methods
        faker_methods = {
            "person": self.generate_person_data,
            "product": self.generate_product_data,
            "weather": self.generate_weather_data,
            # Add more mappings as needed
        }

        throttle_class = self.get_throttles()[0]
        max_data_range = throttle_class.max_data_range
        # Get all instances of the 'type' query parameter
        data_types = request.query_params.getlist("type")

        data_range = int(request.query_params.get("range", 50))
        data_range = min(max_data_range, data_range)
        seed_value = request.query_params.get("seed") or device_id(request)

        try:
            if seed_value and request.user.is_authenticated:
                if request.user.is_paiduser:
                    user_id = str(request.user.id)
                    combined_seed = f"{seed_value}_{user_id}"
                    hashed_seed = int(
                        hashlib.md5(combined_seed.encode("utf-8")).hexdigest(), 16
                    ) % (10**8)
                    self.fake.seed_instance(hashed_seed)
                else:
                    self.fake.seed_instance(seed_value)
        except TypeError:
            pass

        # Check if any 'type' query parameter is provided
        if not data_types:
            return Response(
                {"error": "Query parameter 'type' is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate all provided types and collect Faker methods
        faker_methods_to_use = []
        for data_type in data_types:
            faker_method = faker_methods.get(data_type.lower())
            if not faker_method:
                return Response(
                    {"error": f"Data type '{data_type}' is not supported."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            faker_methods_to_use.append((data_type, faker_method))

        # Generate the data using the Faker methods
        grouped_data = {data_type: [] for data_type, _ in faker_methods_to_use}
        for _ in range(data_range):

            for data_type, faker_method in faker_methods_to_use:
                grouped_data[data_type].append(faker_method())

        filename = "data"
        renderer = request.accepted_renderer
        if isinstance(renderer, PdfRenderer):
            filename += ".pdf"
        elif isinstance(renderer, CsvRenderer):
            filename += "_csv.zip"
        elif isinstance(renderer, ExcelRenderer):
            filename += ".xlsx"
        else:
            response_data = {"data": grouped_data}
            return Response(response_data)

        response_data = {"data": grouped_data}
        response = Response(response_data)
        # Content negotiation will select the ExcelRenderer if the client requests 'excel'
        response["Content-Disposition"] = f"attachment; filename={filename}"
        return response


# class RandomData(APIView, PageNumberPagination):

#     permission_classes = [IsAuthenticatedOrReadOnly]
#     # authentication_classes = [JWTAuthentication]
#     # throttle_classes = [AnonRateThrottle, UserRateThrottle]
#     fake = Faker()

#     def get(self, request):

#         try:
#             faker_methods = {
#                 "name": self.fake.name,
#                 "phone_number": self.fake.basic_phone_number,
#                 "address": self.fake.address,
#                 "country": self.fake.country,
#                 # Add more mappings as needed
#             }

#             # Get all instances of the 'type' query parameter
#             data_types = request.query_params.getlist("type")

#             # Check if any 'type' query parameter is provided
#             if not data_types:
#                 return Response(
#                     {"error": "Query parameter 'type' is required."},
#                     status=status.HTTP_400_BAD_REQUEST,
#                 )

#             # Validate all provided types and collect Faker methods
#             faker_methods_to_use = {}
#             for data_type in data_types:
#                 faker_method = faker_methods.get(data_type)
#                 if not faker_method:
#                     return Response(
#                         {"error": f"Data type '{data_type}' is not supported."},
#                         status=status.HTTP_400_BAD_REQUEST,
#                     )
#                 faker_methods_to_use[data_type] = faker_method

#             if not request.user.is_authenticated:
#                 data_range = 100
#             else:
#                 data_range = int(request.query_params.get("range", 100))

#             data = {
#                 data_type: [faker_method() for _ in range(data_range)]
#                 for data_type, faker_method in faker_methods_to_use.items()
#             }

#             # Convert to array of objects format
#             formatted_data = [
#                 {data_type: data_list} for data_type, data_list in data.items()
#             ]
#         except Exception as e:
#             return Response({"Error": str(e)})
#         return Response({"data": formatted_data})
