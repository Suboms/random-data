import hashlib

import faker_commerce
from faker import Faker
from rest_framework import status
from rest_framework.exceptions import Throttled
from rest_framework.pagination import PageNumberPagination
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


class DummyData(APIView, DataGenerator):
    fake = Faker()
    fake.add_provider(faker_commerce.Provider)
    permission_classes = [IsAuthenticatedOrReadOnly]
    # authentication_classes = [JWTAuthentication]
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

        try:
            if request.user.is_paiduser:
                seed_value = (
                    (request.query_params.get("seed"))
                    if request.user.is_authenticated
                    else device_id(request)
                )
                if request.user.is_authenticated and seed_value is not None:
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
            faker_method = faker_methods.get(data_type)
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
