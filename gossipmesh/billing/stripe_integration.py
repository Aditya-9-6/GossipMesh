class StripeIntegration:
    def charge(self, amount):
        return True

    def update_plan(self, plan_name):
        return f"Plan updated to {plan_name}"
