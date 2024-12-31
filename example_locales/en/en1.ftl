# Welcome message
welcome = Welcome, { $username }!
# Message using a term
-brand-name = Product X
product-intro = You are using { -brand-name }.
# Message with an attribute
login-input =
    .placeholder = Enter your username
# Message with variants based on number
notifications =
    { $count ->
        [0] You have no new notifications.
        [one] You have one new notification.
        [few] You have { $count } new notifications.
       *[many] You have { $count } new notifications.
    }
# Message using a function
current-date = Today's date: { DATETIME($date, month: "long", day: "numeric", year: "numeric") }
# Multiline text
terms =
    Please review our terms of service.
    If you agree, continue using the application.
# Nested placeable
user-info = User: { $user_name } ({ $user_email })
# Using special characters
special-chars = Special characters: { "{" } and { "}" }
# Comment
# This is a comment explaining the following line
logout = Log out
