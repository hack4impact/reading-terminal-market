from flask import render_template, redirect, request, url_for, flash
from flask.ext.login import (
    login_required,
    login_user,
    logout_user,
    current_user
)
from . import account
from ..decorators import merchant_or_vendor_required
from .. import db
from ..email import send_email
from ..models import User, Listing, Vendor
from .forms import (
    LoginForm,
    CreateUserFromInviteForm,
    ChangePasswordForm,
    ChangeEmailForm,
    RequestResetPasswordForm,
    ResetPasswordForm,
    ChangeCompanyNameForm,
    ChangeNameForm,
    CreateMerchantVendorFromInviteForm,
    CSVColumnForm
)


@account.route('/login', methods=['GET', 'POST'])
def login():
    """Log in an existing user."""
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user is not None and user.verify_password(form.password.data):
            login_user(user, form.remember_me.data)
            flash('You are now logged in. Welcome back!', 'success')
            return redirect(request.args.get('next') or url_for('main.index'))
        else:
            flash('Invalid email or password.', 'form-error')
    return render_template('account/login.html', form=form)


@account.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('main.index'))


@account.route('/manage', methods=['GET', 'POST'])
@account.route('/manage/info', methods=['GET', 'POST'])
@login_required
def manage():
    """Display a user's account information."""
    return render_template('account/manage.html', user=current_user, form=None)


@account.route('/reset-password', methods=['GET', 'POST'])
def reset_password_request():
    """Respond to existing user's request to reset their password."""
    if not current_user.is_anonymous():
        return redirect(url_for('main.index'))
    form = RequestResetPasswordForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            token = user.generate_password_reset_token()
            send_email(user.email,
                       'Reset Your Password',
                       'account/email/reset_password',
                       user=user,
                       token=token,
                       next=request.args.get('next'))
        flash('A password reset link has been sent to {}.'
              .format(form.email.data),
              'warning')
        return redirect(url_for('account.login'))
    return render_template('account/reset_password.html', form=form)


@account.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """Reset an existing user's password."""
    if not current_user.is_anonymous():
        return redirect(url_for('main.index'))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user is None:
            flash('Invalid email address.', 'form-error')
            return redirect(url_for('main.index'))
        if user.reset_password(token, form.new_password.data):
            flash('Your password has been updated.', 'form-success')
            return redirect(url_for('account.login'))
        else:
            flash('The password reset link is invalid or has expired.',
                  'form-error')
            return redirect(url_for('main.index'))
    return render_template('account/reset_password.html', form=form)


@account.route('/manage/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    """Change an existing user's password."""
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if current_user.verify_password(form.old_password.data):
            current_user.password = form.new_password.data
            db.session.add(current_user)
            db.session.commit()
            flash('Your password has been updated.', 'form-success')
            return redirect(url_for('main.index'))
        else:
            flash('Original password is invalid.', 'form-error')
    return render_template('account/manage.html', form=form)


@account.route('/manage/change-email', methods=['GET', 'POST'])
@login_required
def change_email_request():
    """Respond to existing user's request to change their email."""
    form = ChangeEmailForm()
    if form.validate_on_submit():
        if current_user.verify_password(form.password.data):
            new_email = form.email.data
            token = current_user.generate_email_change_token(new_email)
            send_email(new_email,
                       'Confirm Your New Email',
                       'account/email/change_email',
                       user=current_user,
                       token=token)
            flash('A confirmation link has been sent to {}.'.format(new_email),
                  'warning')
            return redirect(url_for('main.index'))
        else:
            flash('Invalid email or password.', 'form-error')
    return render_template('account/manage.html', form=form)


@account.route('/manage/change-email/<token>', methods=['GET', 'POST'])
@login_required
def change_email(token):
    """Change existing user's email with provided token."""
    if current_user.change_email(token):
        flash('Your email address has been updated.', 'success')
    else:
        flash('The confirmation link is invalid or has expired.', 'error')
    return redirect(url_for('main.index'))


@account.route('/confirm-account')
@login_required
def confirm_request():
    """Respond to new user's request to confirm their account."""
    token = current_user.generate_confirmation_token()
    send_email(current_user.email, 'Confirm Your Account',
               'account/email/confirm', user=current_user, token=token)
    flash('A new confirmation link has been sent to {}.'.
          format(current_user.email),
          'warning')
    return redirect(url_for('main.index'))


@account.route('/confirm-account/<token>')
@login_required
def confirm(token):
    """Confirm new user's account with provided token."""
    if current_user.confirmed:
        return redirect(url_for('main.index'))
    if current_user.confirm_account(token):
        db.session.commit()
        flash('Your account has been confirmed.', 'success')
    else:
        flash('The confirmation link is invalid or has expired.', 'error')
    return redirect(url_for('main.index'))


@account.route('/join-from-invite/<int:user_id>/<token>',
               methods=['GET', 'POST'])
def join_from_invite(user_id, token):
    """
    Confirm new user's account with provided token and prompt them to set
    a password.
    """
    if current_user is not None and current_user.is_authenticated():
        flash('You are already logged in.', 'error')
        return redirect(url_for('main.index'))

    new_user = User.query.get(user_id)
    if new_user is None:
        return redirect(404)

    if new_user.password_hash is not None:
        if new_user.confirmed is False:
            if new_user.confirm_account(token):
                flash('You have been confirmed.', 'success')
                db.session.commit()
                return redirect(url_for('main.index'))
            else:
                flash('The confirmation link is invalid or has expired. Another '
                      'invite email with a new link has been sent to you.', 'error')
                token = new_user.generate_confirmation_token()
                send_email(new_user.email,
                           'You Are Invited To Join',
                           'account/email/invite',
                           user=new_user,
                           user_id=new_user.id,
                           token=token)
        else:
            flash('You have already confirmed your account', 'error');
            return redirect(url_for('main.index'))

    if new_user.confirm_account(token):
            if new_user.is_admin():
                form = CreateUserFromInviteForm()
            else:
                form = CreateMerchantVendorFromInviteForm()
            if form.validate_on_submit():
                new_user.first_name = form.first_name.data
                new_user.last_name = form.last_name.data
                new_user.password = form.password.data
                if 'company_name' in form:
                    new_user.company_name = form.company_name.data
                db.session.add(new_user)
                db.session.commit()
                flash('Your password has been set. After you log in, you can '
                      'go to the "Your Account" page to review your account '
                      'information and settings.', 'success')
                return redirect(url_for('account.login'))
            return render_template('account/join_invite.html', form=form)
    else:
        flash('The confirmation link is invalid or has expired. Another '
              'invite email with a new link has been sent to you.', 'error')
        token = new_user.generate_confirmation_token()
        send_email(new_user.email,
                   'You Are Invited To Join',
                   'account/email/invite',
                   user=new_user,
                   user_id=new_user.id,
                   token=token)
    return redirect(url_for('main.index'))


@account.before_app_request
def before_request():
    """Force user to confirm email before accessing login-required routes."""
    if current_user.is_authenticated() \
            and not current_user.confirmed \
            and request.endpoint[:8] != 'account.' \
            and request.endpoint != 'static':
        return redirect(url_for('account.unconfirmed'))


@account.route('/unconfirmed')
def unconfirmed():
    """Catch users with unconfirmed emails."""
    if current_user.is_anonymous() or current_user.confirmed:
        return redirect(url_for('main.index'))
    return render_template('account/unconfirmed.html')


@account.route('/manage/change-company-name', methods=['GET', 'POST'])
@login_required
@merchant_or_vendor_required
def change_company_name():
    """Change an existing user's company name."""
    form = ChangeCompanyNameForm()
    if form.validate_on_submit():
        current_user.company_name = form.company_name.data
        db.session.add(current_user)
        db.session.commit()
        flash('Your company name has been updated.', 'form-success')
    return render_template('account/manage.html', form=form)


@account.route('/manage/change-name', methods=['GET', 'POST'])
@login_required
def change_name():
    """Change an existing user's name."""
    form = ChangeNameForm()
    if form.validate_on_submit():
        current_user.first_name = form.first_name.data
        current_user.last_name = form.last_name.data
        db.session.add(current_user)
        db.session.commit()
        flash('Your name has been updated.', 'form-success')
    return render_template('account/manage.html', form=form)

@account.route('/v/<int:profile_id>', methods=['GET','POST'])
@login_required
def profile_page(profile_id):
    vendor = Vendor.query.filter_by(id=profile_id).first()
    f1 = Listing.query.filter_by(name=vendor.f1).first()
    if f1:
        f1_ID = f1
    else:
        f1_ID = f1
    f2 = Listing.query.filter_by(name=vendor.f2).first()
    if f2:
        f2_ID = f2
    else:
        f2_ID = None
    f3 = Listing.query.filter_by(name=vendor.f3).first()
    if f3:
        f3_ID = f3
    else:
        f3_ID = None
    f4 = Listing.query.filter_by(name=vendor.f4).first()
    if f4:
        f4_ID = f4
    else:
        f4_ID = None
    return render_template('vendor/profile.html', vendor=vendor,
                           f1=f1_ID, f2=f2_ID, f3=f3_ID, f4=f4_ID)

@account.route('/manage/csv-settings', methods=['GET', 'POST'])
@login_required
def csv_settings():
    form = CSVColumnForm()
    current_vendor = User.query.filter_by(id=current_user.id).first()
    if form.validate_on_submit():
        current_vendor.product_id_col = form.product_id_col.data
        current_vendor.listing_description_col = form.listing_description_col.data
        current_vendor.price_col = form.price_col.data
        current_vendor.name_col = form.name_col.data
        current_vendor.unit_col = form.unit_col.data
        current_vendor.quantity_col = form.quantity_col.data
        flash('Your CSV settings have been updated.', 'form-success')
        db.session.commit()
    form.product_id_col.data = current_vendor.product_id_col
    form.listing_description_col.data = current_vendor.listing_description_col
    form.price_col.data = current_vendor.price_col
    form.name_col.data = current_vendor.name_col
    form.unit_col.data = current_vendor.unit_col
    form.quantity_col.data = current_vendor.quantity_col
    return render_template('account/manage.html', form=form)

