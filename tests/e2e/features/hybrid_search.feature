Feature: Hybrid Search with BM25 and Vector Ranking
  As a developer searching for code
  I want both keyword and semantic search capabilities
  So that I can find exact matches AND conceptually related code in a single query

  Background:
    Given I am in a git repository

  Scenario: Hybrid search finds exact keyword matches
    Given a repository with files:
      | file_path              | content                          |
      | src/auth/middleware.py | class AuthMiddleware             |
      | src/auth/handlers.py   | def authenticate_user            |
    And the repository is indexed
    When I search for "AuthMiddleware"
    Then the first result should be "src/auth/middleware.py"
    And the result should have BM25 score > 0.7

  Scenario: Hybrid search finds semantic matches
    Given a repository with files:
      | file_path              | content                          |
      | src/auth/middleware.py | class AuthMiddleware             |
      | src/auth/handlers.py   | def authenticate_user            |
    And the repository is indexed
    When I search for "user authentication logic"
    Then results should include both "src/auth/middleware.py" and "src/auth/handlers.py"
    And results should have vector scores > 0.7

  Scenario: Hybrid search combines keyword and semantic ranking
    Given a repository with files:
      | file_path              | content                               |
      | src/auth/jwt.py        | class JWTAuthMiddleware               |
      | src/auth/oauth.py      | class OAuthMiddleware                 |
      | docs/auth_guide.md     | Authentication middleware overview    |
    And the repository is indexed
    When I search for "JWT auth middleware class"
    Then "src/auth/jwt.py" should rank first
    And "src/auth/oauth.py" should rank second
    And "docs/auth_guide.md" should rank lower than "src/auth/oauth.py"
