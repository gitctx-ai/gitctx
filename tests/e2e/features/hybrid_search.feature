Feature: Hybrid Search with BM25 and Vector Ranking
  As a developer searching for code
  I want both keyword and semantic search capabilities
  So that I can find exact matches AND conceptually related code in a single query

  Background:
    Given I am in a git repository

  Scenario: Hybrid search finds exact keyword matches
    Given a repository with files:
      | file_path              | fixture                          |
      | src/auth/middleware.py | hybrid_search/auth_middleware.py |
      | src/auth/handlers.py   | hybrid_search/auth_handlers.py   |
    And the repository is indexed
    When I search for "AuthMiddleware"
    Then the first result should be "src/auth/middleware.py"
    And the result should have BM25 score > 0.7

  Scenario: Hybrid search finds semantic matches
    Given a repository with files:
      | file_path              | fixture                    |
      | src/auth/middleware.py | hybrid_search/auth_middleware.py |
      | src/auth/handlers.py   | hybrid_search/auth_handlers.py   |
    And the repository is indexed
    When I search for "user authentication logic"
    Then results should include both "src/auth/middleware.py" and "src/auth/handlers.py"
    And results should have vector scores > 0.7

  Scenario: Hybrid search combines keyword and semantic ranking
    Given a repository with files:
      | file_path          | fixture                           |
      | src/auth/jwt.py    | hybrid_search/jwt_middleware.py   |
      | src/auth/oauth.py  | hybrid_search/oauth_middleware.py |
    And the repository is indexed
    When I search for "JWT auth middleware class"
    Then "src/auth/jwt.py" should rank first
    And "src/auth/oauth.py" should rank second
