# Generated to keep the Transaction model choices in sync with migrations.
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('transactions', '0002_transaction_loan_payment_alter_transaction_account_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='transaction',
            name='transaction_type',
            field=models.CharField(
                choices=[
                    ('DEPOSIT', 'Deposit'),
                    ('WITHDRAWAL', 'Withdrawal'),
                    ('INTEREST', 'Interest Credit'),
                    ('REVERSAL', 'Reversal'),
                    ('LOAN_DISBURSEMENT', 'Loan Disbursement'),
                    ('LOAN_REPAYMENT', 'Loan Repayment'),
                ],
                max_length=20,
            ),
        ),
    ]
