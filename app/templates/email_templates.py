"""
Enhanced Email Templates for Agno WorkSphere
Comprehensive email templates with modern styling and responsive design
"""

from typing import Optional, Dict, Any


class EmailTemplates:
    """Enhanced email templates with modern styling"""
    
    @staticmethod
    def get_base_styles() -> str:
        """Get base CSS styles for all email templates"""
        return """
        <style>
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
                line-height: 1.6;
                color: #333;
                margin: 0;
                padding: 0;
                background-color: #f8fafc;
            }
            .email-container {
                max-width: 600px;
                margin: 0 auto;
                background-color: #ffffff;
                border-radius: 12px;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                overflow: hidden;
            }
            .header {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 30px;
                text-align: center;
            }
            .header h1 {
                margin: 0;
                font-size: 28px;
                font-weight: 600;
            }
            .header .subtitle {
                margin: 8px 0 0 0;
                font-size: 16px;
                opacity: 0.9;
            }
            .content {
                padding: 40px 30px;
            }
            .invitation-card {
                background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
                color: white;
                padding: 25px;
                border-radius: 10px;
                margin: 20px 0;
                text-align: center;
            }
            .role-badge {
                display: inline-block;
                padding: 8px 16px;
                border-radius: 20px;
                font-weight: 600;
                font-size: 14px;
                margin: 10px 0;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }
            .credentials {
                background: #f8fafc;
                border: 2px solid #e2e8f0;
                border-radius: 8px;
                padding: 20px;
                margin: 25px 0;
            }
            .credentials h3 {
                margin: 0 0 15px 0;
                color: #2d3748;
                font-size: 18px;
            }
            .button {
                display: inline-block;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white !important;
                padding: 15px 30px;
                text-decoration: none;
                border-radius: 8px;
                font-weight: 600;
                font-size: 16px;
                margin: 20px 0;
                transition: transform 0.2s;
            }
            .button:hover {
                transform: translateY(-2px);
            }
            .features {
                background: #f7fafc;
                border-radius: 8px;
                padding: 20px;
                margin: 25px 0;
            }
            .features h3 {
                color: #2d3748;
                margin: 0 0 15px 0;
            }
            .features ul {
                margin: 0;
                padding-left: 20px;
            }
            .features li {
                margin: 8px 0;
                color: #4a5568;
            }
            .footer {
                background: #2d3748;
                color: #a0aec0;
                padding: 25px 30px;
                text-align: center;
                font-size: 14px;
            }
            .footer p {
                margin: 5px 0;
            }
            .warning {
                background: #fed7d7;
                border: 1px solid #feb2b2;
                color: #c53030;
                padding: 12px;
                border-radius: 6px;
                margin: 15px 0;
                font-size: 14px;
            }
            .success {
                background: #c6f6d5;
                border: 1px solid #9ae6b4;
                color: #22543d;
                padding: 12px;
                border-radius: 6px;
                margin: 15px 0;
            }
            .code {
                background: #e2e8f0;
                padding: 4px 8px;
                border-radius: 4px;
                font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
                font-size: 14px;
            }
            @media only screen and (max-width: 600px) {
                .email-container {
                    margin: 0;
                    border-radius: 0;
                }
                .header, .content, .footer {
                    padding: 20px;
                }
                .button {
                    display: block;
                    text-align: center;
                }
            }
        </style>
        """
    
    @staticmethod
    def get_organization_invitation_template(
        inviter_name: str,
        organization_name: str,
        role: str,
        to_email: str,
        temp_password: str,
        invitation_url: str,
        custom_message: Optional[str] = None
    ) -> str:
        """Enhanced organization invitation template"""
        
        role_colors = {
            'owner': '#e53e3e',
            'admin': '#38b2ac',
            'member': '#3182ce',
            'viewer': '#718096'
        }
        role_color = role_colors.get(role.lower(), '#3182ce')
        
        custom_message_html = ""
        if custom_message:
            custom_message_html = f"""
            <div style="background: white; border-left: 4px solid #667eea; padding: 15px; margin: 20px 0; border-radius: 0 6px 6px 0;">
                <p style="margin: 0; font-style: italic; color: #4a5568;">"{custom_message}"</p>
            </div>
            """
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Organization Invitation - {organization_name}</title>
            {EmailTemplates.get_base_styles()}
        </head>
        <body>
            <div class="email-container">
                <div class="header">
                    <h1>🏢 Organization Invitation</h1>
                    <p class="subtitle">Join {organization_name} on Agno WorkSphere</p>
                </div>
                
                <div class="content">
                    <p style="font-size: 18px; margin-bottom: 25px;">Hello there! 👋</p>
                    
                    <div class="invitation-card">
                        <p style="margin: 0 0 15px 0; font-size: 18px;"><strong>{inviter_name}</strong> has invited you to join</p>
                        <h2 style="margin: 0; font-size: 24px;">{organization_name}</h2>
                        <div class="role-badge" style="background-color: {role_color};">{role.title()}</div>
                    </div>
                    
                    {custom_message_html}
                    
                    <div class="credentials">
                        <h3>🔐 Your Login Credentials</h3>
                        <p><strong>Email:</strong> {to_email}</p>
                        <p><strong>Temporary Password:</strong> <span class="code">{temp_password}</span></p>
                        <div class="warning">
                            ⚠️ Please change your password after your first login for security.
                        </div>
                    </div>
                    
                    <div style="text-align: center; margin: 30px 0;">
                        <a href="{invitation_url}" class="button">🚀 Accept Invitation</a>
                    </div>
                    
                    <div class="features">
                        <h3>🎯 What you'll get access to:</h3>
                        <ul>
                            <li>📊 Organization dashboard and analytics</li>
                            <li>👥 Team collaboration tools</li>
                            <li>📋 Project management workspace</li>
                            <li>💬 Real-time communication</li>
                            <li>📁 File sharing and storage</li>
                            <li>⚡ Workflow automation</li>
                        </ul>
                    </div>
                    
                    <p>We're excited to have you join our team and start collaborating!</p>
                    <p><strong>The Agno WorkSphere Team</strong></p>
                </div>
                
                <div class="footer">
                    <p>This invitation was sent to {to_email}</p>
                    <p>© 2024 Agno WorkSphere. All rights reserved.</p>
                    <p>Need help? Contact our support team</p>
                </div>
            </div>
        </body>
        </html>
        """
    
    @staticmethod
    def get_project_invitation_template(
        inviter_name: str,
        organization_name: str,
        project_name: str,
        role: str,
        to_email: str,
        temp_password: str,
        invitation_url: str,
        custom_message: Optional[str] = None
    ) -> str:
        """Enhanced project invitation template"""
        
        role_colors = {
            'owner': '#e53e3e',
            'admin': '#38b2ac',
            'member': '#3182ce',
            'viewer': '#718096'
        }
        role_color = role_colors.get(role.lower(), '#3182ce')
        
        custom_message_html = ""
        if custom_message:
            custom_message_html = f"""
            <div style="background: white; border-left: 4px solid #48bb78; padding: 15px; margin: 20px 0; border-radius: 0 6px 6px 0;">
                <p style="margin: 0; font-style: italic; color: #4a5568;">"{custom_message}"</p>
            </div>
            """
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Project Invitation - {project_name}</title>
            {EmailTemplates.get_base_styles()}
        </head>
        <body>
            <div class="email-container">
                <div class="header" style="background: linear-gradient(135deg, #48bb78 0%, #38a169 100%);">
                    <h1>📋 Project Invitation</h1>
                    <p class="subtitle">Collaborate on {project_name}</p>
                </div>
                
                <div class="content">
                    <p style="font-size: 18px; margin-bottom: 25px;">Ready to build something amazing? 🚀</p>
                    
                    <div class="invitation-card" style="background: linear-gradient(135deg, #48bb78 0%, #38a169 100%);">
                        <p style="margin: 0 0 10px 0; font-size: 16px;"><strong>{inviter_name}</strong> has invited you to collaborate on</p>
                        <h2 style="margin: 0 0 5px 0; font-size: 24px;">{project_name}</h2>
                        <p style="margin: 0 0 15px 0; opacity: 0.9;">in {organization_name}</p>
                        <div class="role-badge" style="background-color: {role_color};">{role.title()}</div>
                    </div>
                    
                    {custom_message_html}
                    
                    <div class="credentials">
                        <h3>🔐 Your Login Credentials</h3>
                        <p><strong>Email:</strong> {to_email}</p>
                        <p><strong>Temporary Password:</strong> <span class="code">{temp_password}</span></p>
                        <div class="warning">
                            ⚠️ Please change your password after your first login for security.
                        </div>
                    </div>
                    
                    <div style="text-align: center; margin: 30px 0;">
                        <a href="{invitation_url}" class="button" style="background: linear-gradient(135deg, #48bb78 0%, #38a169 100%);">🎯 Join Project</a>
                    </div>
                    
                    <div class="features">
                        <h3>🛠️ What you'll be able to do:</h3>
                        <ul>
                            <li>📊 Track project progress and milestones</li>
                            <li>✅ Create and manage tasks</li>
                            <li>📋 Use Kanban boards for workflow</li>
                            <li>💬 Collaborate with team members</li>
                            <li>📎 Share files and resources</li>
                            <li>⏰ Set deadlines and priorities</li>
                            <li>📈 View project analytics and reports</li>
                        </ul>
                    </div>
                    
                    <div class="success">
                        <strong>🎉 Welcome to the project team!</strong> We're excited to have you contribute to {project_name}.
                    </div>
                    
                    <p><strong>The Agno WorkSphere Team</strong></p>
                </div>
                
                <div class="footer">
                    <p>This invitation was sent to {to_email}</p>
                    <p>© 2024 Agno WorkSphere. All rights reserved.</p>
                    <p>Need help? Contact our support team</p>
                </div>
            </div>
        </body>
        </html>
        """

    @staticmethod
    def get_board_invitation_template(
        inviter_name: str,
        organization_name: str,
        project_name: str,
        board_name: str,
        role: str,
        to_email: str,
        temp_password: str,
        invitation_url: str,
        custom_message: Optional[str] = None
    ) -> str:
        """Enhanced board invitation template"""

        role_colors = {
            'owner': '#e53e3e',
            'admin': '#38b2ac',
            'member': '#3182ce',
            'viewer': '#718096'
        }
        role_color = role_colors.get(role.lower(), '#3182ce')

        custom_message_html = ""
        if custom_message:
            custom_message_html = f"""
            <div style="background: white; border-left: 4px solid #ed8936; padding: 15px; margin: 20px 0; border-radius: 0 6px 6px 0;">
                <p style="margin: 0; font-style: italic; color: #4a5568;">"{custom_message}"</p>
            </div>
            """

        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Board Invitation - {board_name}</title>
            {EmailTemplates.get_base_styles()}
        </head>
        <body>
            <div class="email-container">
                <div class="header" style="background: linear-gradient(135deg, #ed8936 0%, #dd6b20 100%);">
                    <h1>📋 Board Invitation</h1>
                    <p class="subtitle">Join the {board_name} board</p>
                </div>

                <div class="content">
                    <p style="font-size: 18px; margin-bottom: 25px;">Time to get organized! 📋</p>

                    <div class="invitation-card" style="background: linear-gradient(135deg, #ed8936 0%, #dd6b20 100%);">
                        <p style="margin: 0 0 10px 0; font-size: 16px;"><strong>{inviter_name}</strong> has invited you to collaborate on</p>
                        <h2 style="margin: 0 0 5px 0; font-size: 24px;">{board_name}</h2>
                        <p style="margin: 0 0 5px 0; opacity: 0.9;">in {project_name} project</p>
                        <p style="margin: 0 0 15px 0; opacity: 0.8; font-size: 14px;">{organization_name}</p>
                        <div class="role-badge" style="background-color: {role_color};">{role.title()}</div>
                    </div>

                    {custom_message_html}

                    <div class="credentials">
                        <h3>🔐 Your Login Credentials</h3>
                        <p><strong>Email:</strong> {to_email}</p>
                        <p><strong>Temporary Password:</strong> <span class="code">{temp_password}</span></p>
                        <div class="warning">
                            ⚠️ Please change your password after your first login for security.
                        </div>
                    </div>

                    <div style="text-align: center; margin: 30px 0;">
                        <a href="{invitation_url}" class="button" style="background: linear-gradient(135deg, #ed8936 0%, #dd6b20 100%);">📋 Access Board</a>
                    </div>

                    <div class="features">
                        <h3>🎯 What you'll be able to do on this board:</h3>
                        <ul>
                            <li>📋 View and manage board cards</li>
                            <li>✅ Create and assign tasks</li>
                            <li>🔄 Move cards between columns (To Do, In Progress, Done)</li>
                            <li>💬 Comment and collaborate on tasks</li>
                            <li>📎 Attach files and resources</li>
                            <li>⏰ Set due dates and priorities</li>
                            <li>🏷️ Add labels and tags</li>
                            <li>📊 Track board progress and metrics</li>
                        </ul>
                    </div>

                    <div style="background: #fef5e7; border: 1px solid #f6ad55; border-radius: 8px; padding: 20px; margin: 25px 0;">
                        <h4 style="margin: 0 0 10px 0; color: #c05621;">🚀 Board Features</h4>
                        <p style="margin: 0; color: #744210;">This Kanban board helps you visualize work, limit work-in-progress, and maximize efficiency. Perfect for agile project management!</p>
                    </div>

                    <p>Ready to organize and get things done! We're excited to have you aboard.</p>
                    <p><strong>The Agno WorkSphere Team</strong></p>
                </div>

                <div class="footer">
                    <p>This invitation was sent to {to_email}</p>
                    <p>© 2024 Agno WorkSphere. All rights reserved.</p>
                    <p>Need help? Contact our support team</p>
                </div>
            </div>
        </body>
        </html>
        """

    @staticmethod
    def get_text_version(template_type: str, **kwargs) -> str:
        """Get plain text version of email templates"""

        if template_type == "organization":
            return f"""
🏢 Organization Invitation - {kwargs['organization_name']}

Hello!

{kwargs['inviter_name']} has invited you to join {kwargs['organization_name']} on Agno WorkSphere as a {kwargs['role'].title()}.

{f'Message: "{kwargs["custom_message"]}"' if kwargs.get('custom_message') else ''}

Your login credentials:
Email: {kwargs['to_email']}
Temporary Password: {kwargs['temp_password']}

Accept your invitation: {kwargs['invitation_url']}

Please change your password after your first login for security.

What you'll get access to:
- Organization dashboard and analytics
- Team collaboration tools
- Project management workspace
- Real-time communication
- File sharing and storage
- Workflow automation

We're excited to have you join our team!
The Agno WorkSphere Team
            """

        elif template_type == "project":
            return f"""
📋 Project Invitation - {kwargs['project_name']}

Ready to build something amazing?

{kwargs['inviter_name']} has invited you to collaborate on {kwargs['project_name']} in {kwargs['organization_name']} as a {kwargs['role'].title()}.

{f'Message: "{kwargs["custom_message"]}"' if kwargs.get('custom_message') else ''}

Your login credentials:
Email: {kwargs['to_email']}
Temporary Password: {kwargs['temp_password']}

Accept your invitation: {kwargs['invitation_url']}

Please change your password after your first login for security.

What you'll be able to do:
- Track project progress and milestones
- Create and manage tasks
- Use Kanban boards for workflow
- Collaborate with team members
- Share files and resources
- Set deadlines and priorities
- View project analytics and reports

Welcome to the project team!
The Agno WorkSphere Team
            """

        elif template_type == "board":
            return f"""
📋 Board Invitation - {kwargs['board_name']}

Time to get organized!

{kwargs['inviter_name']} has invited you to collaborate on the {kwargs['board_name']} board in {kwargs['project_name']} project as a {kwargs['role'].title()}.

Organization: {kwargs['organization_name']}
{f'Message: "{kwargs["custom_message"]}"' if kwargs.get('custom_message') else ''}

Your login credentials:
Email: {kwargs['to_email']}
Temporary Password: {kwargs['temp_password']}

Accept your invitation: {kwargs['invitation_url']}

Please change your password after your first login for security.

What you'll be able to do on this board:
- View and manage board cards
- Create and assign tasks
- Move cards between columns
- Comment and collaborate on tasks
- Attach files and resources
- Set due dates and priorities
- Add labels and tags
- Track board progress and metrics

Ready to organize and get things done!
The Agno WorkSphere Team
            """

        return "Email template not found."


# Convenience functions for easy template access
def get_organization_invitation_email(
    inviter_name: str,
    organization_name: str,
    role: str,
    to_email: str,
    temp_password: str,
    invitation_url: str,
    custom_message: Optional[str] = None
) -> tuple[str, str]:
    """Get organization invitation email HTML and text versions"""
    html = EmailTemplates.get_organization_invitation_template(
        inviter_name, organization_name, role, to_email,
        temp_password, invitation_url, custom_message
    )
    text = EmailTemplates.get_text_version(
        "organization", inviter_name=inviter_name, organization_name=organization_name,
        role=role, to_email=to_email, temp_password=temp_password,
        invitation_url=invitation_url, custom_message=custom_message
    )
    return html, text


def get_project_invitation_email(
    inviter_name: str,
    organization_name: str,
    project_name: str,
    role: str,
    to_email: str,
    temp_password: str,
    invitation_url: str,
    custom_message: Optional[str] = None
) -> tuple[str, str]:
    """Get project invitation email HTML and text versions"""
    html = EmailTemplates.get_project_invitation_template(
        inviter_name, organization_name, project_name, role, to_email,
        temp_password, invitation_url, custom_message
    )
    text = EmailTemplates.get_text_version(
        "project", inviter_name=inviter_name, organization_name=organization_name,
        project_name=project_name, role=role, to_email=to_email,
        temp_password=temp_password, invitation_url=invitation_url,
        custom_message=custom_message
    )
    return html, text


def get_board_invitation_email(
    inviter_name: str,
    organization_name: str,
    project_name: str,
    board_name: str,
    role: str,
    to_email: str,
    temp_password: str,
    invitation_url: str,
    custom_message: Optional[str] = None
) -> tuple[str, str]:
    """Get board invitation email HTML and text versions"""
    html = EmailTemplates.get_board_invitation_template(
        inviter_name, organization_name, project_name, board_name, role,
        to_email, temp_password, invitation_url, custom_message
    )
    text = EmailTemplates.get_text_version(
        "board", inviter_name=inviter_name, organization_name=organization_name,
        project_name=project_name, board_name=board_name, role=role,
        to_email=to_email, temp_password=temp_password,
        invitation_url=invitation_url, custom_message=custom_message
    )
    return html, text
