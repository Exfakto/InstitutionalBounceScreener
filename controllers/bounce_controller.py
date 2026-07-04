from services.bounce_validation_service import BounceValidationService


class BounceController:
    """
    Controller responsible for bounce validation actions.
    """

    def __init__(self, bounce_validation_service=None):
        self.bounces = bounce_validation_service or BounceValidationService()

    def validate_bounces(self):
        """
        Validate stored support levels.
        """

        return self.bounces.validate_bounces()

    def close(self):
        self.bounces.close()
