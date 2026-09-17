from healthtech_service import AppointmentRequest, Listing, aggregate_listings, patient_safe_notification


class FakeEmbedder:
    vectors = {"cardiology clinic": [1.0, 0.0], "Heart Care cardiology": [1.0, 0.0], "Dental Hub dentistry": [0.0, 1.0]}

    def embed(self, text: str):
        return self.vectors[text]


def test_aggregation_prefers_matching_specialty_and_notification_is_minimal():
    listings = [Listing("a", "Heart Care", "cardiology", "https://a.test/book"), Listing("b", "Dental Hub", "dentistry", "https://b.test/book")]
    ranked = aggregate_listings("cardiology clinic", listings, FakeEmbedder())
    assert ranked[0]["name"] == "Heart Care"
    notice = patient_safe_notification(AppointmentRequest("p-42", "Heart Care", "2026-09-04T09:00:00Z"))
    assert notice.contains_patient_data is False
    assert "p-42" not in notice.message
