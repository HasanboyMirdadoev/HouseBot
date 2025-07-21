class HouseManager:
    def __init__(self, db: Database):
        self.db = db

    def get_houses_by_district(self, district):
        houses = self.db.fetchall(
            "SELECT id, district, description, price, location FROM houses WHERE district=%s",
            (district,)
        )
        return [self._house_with_images(house) for house in houses]

    def get_houses_by_location(self, location_keyword):
        houses = self.db.fetchall(
            "SELECT id, district, description, price, location FROM houses WHERE location ILIKE %s",
            (f"%{location_keyword}%",)
        )
        return [self._house_with_images(house) for house in houses]

    def _house_with_images(self, house_tuple):
        house_id, district, description, price, location = house_tuple
        images = self.db.fetchall(
            "SELECT image_url FROM house_images WHERE house_id=%s", (house_id,)
        )
        image_urls = [img[0] for img in images]
        return {
            "id": house_id,
            "district": district,
            "description": description,
            "price": price,
            "location": location,
            "images": image_urls
        }

    def add_house(self, district, description, price, location):
        house_id = self.db.execute(
            "INSERT INTO houses (district, description, price, location) VALUES (%s, %s, %s, %s) RETURNING id",
            (district, description, price, location),
            returning=True
        )[0]
        return house_id

    def add_image(self, house_id, image_url):
        self.db.execute(
            "INSERT INTO house_images (house_id, image_url) VALUES (%s, %s)",
            (house_id, image_url)
        )

    def update_house(self, house_id, district, description, price, location):
        self.db.execute(
            "UPDATE houses SET district=%s, description=%s, price=%s, location=%s WHERE id=%s",
            (district, description, price, location, house_id)
        )

    def delete_house(self, house_id):
        images = self.db.fetchall("SELECT image_url FROM house_images WHERE house_id=%s", (house_id,))
        for image_url in images:
            vercel_blob.delete(image_url[0])
        self.db.execute("DELETE FROM house_images WHERE house_id=%s", (house_id,))
        self.db.execute("DELETE FROM houses WHERE id=%s", (house_id,))

    def update_images(self, house_id, new_image_urls):
        old_images = self.db.fetchall("SELECT image_url FROM house_images WHERE house_id=%s", (house_id,))
        for image in old_images:
            vercel_blob.delete(image[0])
        self.db.execute("DELETE FROM house_images WHERE house_id=%s", (house_id,))
        for url in new_image_urls:
            self.add_image(house_id, url)