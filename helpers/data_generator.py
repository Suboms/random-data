import faker_commerce
from faker import Faker


class DataGenerator:
    fake = Faker()
    fake.add_provider(faker_commerce.Provider)

    def generate_phone_num(self):
        country_code = self.fake.country_calling_code()
        phone_num = self.fake.numerify("##########")
        return f"{country_code}{phone_num}"

    def generate_person_data(self):
        return {
            "name": self.fake.name(),
            "age": self.fake.random_int(min=18, max=80),
            "gender": self.fake.random_element(elements=("Male", "Female")),
            "nationality": self.fake.country(),
            "phone_number": self.generate_phone_num(),
            "address": self.fake.address().replace("\n", " ").strip(),
            "email": self.fake.email(domain="gmail.com"),
        }

    def generate_weather_data(self):
        return {
            "temperature": f"{self.fake.random_int(min=25, max=45)}\u00b0C",
            "humidity": f"{self.fake.random_int(min=0, max=100)}%",
            "condition": self.fake.random_element(
                elements=("Sunny", "Rainy", "Cloudy", "Snowy")
            ),
            "wind_speed": f"{round(self.fake.random_number(digits=2, fix_len=True) / 10, 1)} km/h",
            "city": self.fake.city(),
            "country": self.fake.country(),
        }

    def generate_product_data(self):
        return {
            "name": self.fake.ecommerce_name(),
            "category": self.fake.ecommerce_category(),
            "price": f"${round(self.fake.random_number(digits=5) / 100, 2)}",
            "stock": self.fake.random_int(min=0, max=1000),
            "sku": self.fake.ean13(),
        }


