from iommi.admin import Admin

class CobbledAdmin(Admin):
    class Meta:
        apps__app_dataset__include = True
        apps__app_instrument__include = True
        apps__app_observation__include = True
        apps__app_project__include = True
        apps__app_proposal__include = True
        apps__app_source__include = True
        apps__app_sourcegaiainfo__include = True
        apps__app_researcher__include = True
        apps__app_fluxunit__include = True
        apps__app_wavelengthunit__include = True
        
        # Customize User edit form (parts__edit_auth_user)
        parts__edit_auth_user__auto__include = [
            'username', 'email', 'first_name', 'last_name', 'is_staff', 'is_active', 'is_superuser', 'password'
        ]
        parts__edit_auth_user__fields__password__required = False
        parts__edit_auth_user__fields__password__write_to_instance = lambda instance, value, **_: instance.set_password(value) if value else None
        parts__edit_auth_user__fields__password__read_from_instance = lambda **_: ""
