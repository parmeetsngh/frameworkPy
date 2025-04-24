@automated
@story_based
Feature: story_based_feature
  Feature file for story_based test scenarios

  Scenario: Verify functionality from story requirements
    Given the application is running
    When the user performs the required action {"user_id": "test_user", "password": "test_password"}
    Then the system responds correctly

