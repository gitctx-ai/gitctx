Feature: HEAD Boosting
  As a developer searching for code
  I want current HEAD code to rank higher than historical versions
  So that I see the most up-to-date implementation first (not deprecated code from old commits)

  Background:
    Given gitctx is installed

  Scenario: HEAD code ranks higher than historical code
    Given a repository with files at different commits:
      | file_path           | content              | is_head |
      | src/auth/current.py | class AuthMiddleware | true    |
      | src/auth/old.py     | class OldAuth        | false   |
    When I search for "auth"
    Then "src/auth/current.py" should rank above "src/auth/old.py"
    And HEAD results should have 1.5x boost applied

  Scenario: Boost applies to hybrid scores, not absolute ranking
    Given a repository with files:
      | file_path           | content                    | is_head | hybrid_score |
      | src/auth/current.py | def authenticate           | true    | 0.6          |
      | src/auth/old.py     | class AuthenticationSystem | false   | 0.95         |
    When I search for "authentication system"
    Then "src/auth/old.py" should rank first with score 0.95
    And boost does not override semantic relevance

  Scenario: Equal semantic matches prefer HEAD code
    Given a repository with files:
      | file_path           | content              | is_head | hybrid_score |
      | src/auth/current.py | class AuthMiddleware | true    | 0.8          |
      | src/auth/old.py     | class AuthMiddleware | false   | 0.8          |
    When I search for "AuthMiddleware"
    Then "src/auth/current.py" should rank first with boosted score 1.2
    And HEAD boost breaks ties
