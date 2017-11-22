Emails sent by the backend app

# Registration

## New account created (we send URL to confirm email)
Condition: user filled sign-up form
Filename: registration_01.html

## Email confirmed
Condition: user confirmed his email and did not sign in for 15 min
Filename: registration_02.html


# KYC

## KYC data received
Condition: user filled the KYC form
Filename: kyc_01.html

## Account rejected
Condition: rejected the KYC submissionaccount is rejected
Filename: kyc_02.html


# Account

## Password change request (we send URL to change password)
Condition: user requested password reset via dashboard
Filename: account_01_1.html

## Password changed
Condition: user successfully changed password
Filename: account_01_2.html

## ETH address changed
Condition: user changed his ETH address via dashboard
Filename: account_02.html


# Transactions

## We received BTC/ETH transaction
Condition: we received ETH/BTC
Filename: transactions_01.html

## We received withdrawal request
Condition: user requested withdrawal of JNT
Filename: transactions_02.html

## We received withdrawal request (TODO)
Condition: user requested withdrawal of JNT, send email with confirmation 
Filename: transactions_02_2.html

# Withdrawal of JNT succeeded
Condition: we processed user`s request to withdraw JNT
Filename: transactions_03.html

# We received BTC/ETH, but JNT are sold out
Condition: we received ETH/BTC, but all JNT are sold out -> we will return BTC/ETH back manually
Filename: transactions_04.html
