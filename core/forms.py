from django import forms
from .models import Profile


class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ["name", "age", "gender", "looking_for", "city", "level", "style",
                  "bio", "photo", "allow_whatsapp"]
        widgets = {"bio": forms.Textarea(attrs={"rows": 3})}

    def clean_age(self):
        age = self.cleaned_data["age"]
        if age < 18 or age > 80:
            raise forms.ValidationError("Age must be between 18 and 80.")
        return age

    def clean_photo(self):
        photo = self.cleaned_data.get("photo")
        if photo and hasattr(photo, "size") and photo.size > 3 * 1024 * 1024:
            raise forms.ValidationError("Photo must be smaller than 3 MB.")
        return photo
