import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from io import BytesIO, StringIO

# Page configuration
st.set_page_config(page_title="CloudMart Cost Governance Dashboard", layout="wide", page_icon="☁️")

# Title and description
st.title("☁️ CloudMart Resource Tagging & Cost Governance Dashboard")
st.markdown("""
This dashboard analyzes cloud resource tagging compliance and cost visibility for CloudMart Inc.
Upload your CSV file to begin the analysis.
""")

# File uploader
uploaded_file = st.file_uploader("📂 Upload CloudMart CSV File", type=['csv'])

# Initialize session state for edited data
if 'df_edited' not in st.session_state:
    st.session_state.df_edited = None
if 'original_df' not in st.session_state:
    st.session_state.original_df = None

# Load data function with RIGHT-ALIGNED parsing (last 3 columns always have values)
@st.cache_data
def load_data(file):
    try:
        # Read the file content
        content = file.read()
        
        # Decode if bytes
        if isinstance(content, bytes):
            content = content.decode('utf-8')
        
        # Split into lines
        lines = content.strip().split('\n')
        
        # Get header
        header_line = lines[0].strip()
        if header_line.startswith('"') and header_line.endswith('"'):
            header_line = header_line[1:-1]
        
        headers = [h.strip() for h in header_line.split(',')]
        expected_cols = len(headers)
        
        # Process data rows with RIGHT-ALIGNMENT
        # Last 3 columns (CreatedBy, MonthlyCostUSD, Tagged) ALWAYS have values
        data_rows = []
        for i, line in enumerate(lines[1:], start=1):
            line = line.strip()
            
            # Remove surrounding quotes
            if line.startswith('"') and line.endswith('"'):
                line = line[1:-1]
            
            # Split by comma
            fields = line.split(',')
            
            # If row has fewer fields than expected, RIGHT-ALIGN the last 3 columns
            if len(fields) < expected_cols:
                missing_count = expected_cols - len(fields)
                
                # Last 3 fields are always: CreatedBy, MonthlyCostUSD, Tagged
                first_part = fields[:-3]  # Everything except last 3
                last_three = fields[-3:]   # Last 3 fields that always have values
                
                # Insert empty fields in the middle (between first_part and last_three)
                padding = [''] * missing_count
                fields = first_part + padding + last_three
            
            # If row has more fields, truncate (shouldn't happen but just in case)
            elif len(fields) > expected_cols:
                fields = fields[:expected_cols]
            
            data_rows.append(fields)
        
        # Create DataFrame
        df = pd.DataFrame(data_rows, columns=headers)
        
        # Strip whitespace from all string columns
        for col in df.columns:
            if df[col].dtype == 'object':
                df[col] = df[col].str.strip()
        
        # Replace empty strings with NaN for better handling
        df.replace('', pd.NA, inplace=True)
        
        # Convert MonthlyCostUSD to numeric
        if 'MonthlyCostUSD' in df.columns:
            df['MonthlyCostUSD'] = pd.to_numeric(df['MonthlyCostUSD'], errors='coerce')
        
        return df
        
    except Exception as e:
        st.error(f"Error loading file: {e}")
        st.info("Debug info: Please check if your CSV file is properly formatted.")
        import traceback
        st.code(traceback.format_exc())
        return None

# Main application logic
if uploaded_file is not None:
    df = load_data(uploaded_file)
    
    if df is not None and not df.empty:
        # Store original dataframe
        if st.session_state.original_df is None:
            st.session_state.original_df = df.copy()
        
        # Check if required columns exist
        required_columns = ['ResourceID', 'Service', 'MonthlyCostUSD', 'Tagged']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            st.error(f"❌ Missing required columns: {', '.join(missing_columns)}")
            st.info("**Available columns in your file:**")
            st.write(df.columns.tolist())
            st.info("**Required columns:**")
            st.write(required_columns)
            st.stop()
        
        # ============================================
        # SIDEBAR - NAVIGATION & FILTERS
        # ============================================
        st.sidebar.title("📊 Navigation")
        task_set = st.sidebar.radio(
            "Select Task Set:",
            ["Overview", "Task 1: Data Exploration", "Task 2: Cost Visibility", 
             "Task 3: Tagging Compliance", "Task 4: Visualization Dashboard", 
             "Task 5: Tag Remediation"]
        )
        
        st.sidebar.markdown("---")
        st.sidebar.title("🔍 Global Filters")
        st.sidebar.info("These filters apply to all task sets")
        
        # Service Filter
        services = ['All'] + sorted(df['Service'].unique().tolist())
        selected_service = st.sidebar.selectbox("Filter by Service", services, key='service_filter')
        
        # Region Filter
        if 'Region' in df.columns:
            regions = ['All'] + sorted(df['Region'].unique().tolist())
            selected_region = st.sidebar.selectbox("Filter by Region", regions, key='region_filter')
        else:
            selected_region = 'All'
        
        # Department Filter
        if 'Department' in df.columns:
            departments = ['All'] + sorted(df['Department'].dropna().unique().tolist())
            selected_department = st.sidebar.selectbox("Filter by Department", departments, key='department_filter')
        else:
            selected_department = 'All'
        
        # Environment Filter
        if 'Environment' in df.columns:
            environments = ['All'] + sorted(df['Environment'].dropna().unique().tolist())
            selected_environment = st.sidebar.selectbox("Filter by Environment", environments, key='environment_filter')
        else:
            selected_environment = 'All'
        
        # Tagged Status Filter
        tagged_options = ['All', 'Yes', 'No']
        selected_tagged = st.sidebar.selectbox("Filter by Tagged Status", tagged_options, key='tagged_filter')
        
        # Apply Filters
        filtered_df = df.copy()
        
        if selected_service != 'All':
            filtered_df = filtered_df[filtered_df['Service'] == selected_service]
        
        if selected_region != 'All' and 'Region' in df.columns:
            filtered_df = filtered_df[filtered_df['Region'] == selected_region]
        
        if selected_department != 'All' and 'Department' in df.columns:
            filtered_df = filtered_df[filtered_df['Department'] == selected_department]
        
        if selected_environment != 'All' and 'Environment' in df.columns:
            filtered_df = filtered_df[filtered_df['Environment'] == selected_environment]
        
        if selected_tagged != 'All':
            filtered_df = filtered_df[filtered_df['Tagged'] == selected_tagged]
        
        # Display filter summary
        st.sidebar.markdown("---")
        st.sidebar.metric("Filtered Resources", len(filtered_df))
        st.sidebar.metric("Filtered Cost", f"${filtered_df['MonthlyCostUSD'].sum():,.2f}")
        
        # Reset filters button
        if st.sidebar.button("🔄 Reset All Filters"):
            st.rerun()
        
        # ============================================
        # OVERVIEW PAGE
        # ============================================
        if task_set == "Overview":
            st.header("📋 Lab Overview")
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Total Resources", len(filtered_df))
            with col2:
                total_cost = filtered_df['MonthlyCostUSD'].sum()
                st.metric("Total Monthly Cost", f"${total_cost:,.2f}")
            with col3:
                tagged_pct = (filtered_df['Tagged'].value_counts().get('Yes', 0) / len(filtered_df)) * 100 if len(filtered_df) > 0 else 0
                st.metric("Tagged Resources", f"{tagged_pct:.1f}%")
            with col4:
                departments = filtered_df['Department'].nunique() if 'Department' in filtered_df.columns else 0
                st.metric("Departments", departments)
            
            st.markdown("---")
            st.subheader("Dataset Preview")
            st.dataframe(filtered_df.head(10), use_container_width=True)
            
            # Display column information
            st.markdown("---")
            st.subheader("📊 Dataset Information")
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**Columns:**", len(filtered_df.columns))
                st.write("**Rows:**", len(filtered_df))
            
            with col2:
                st.write("**Column Names:**")
                st.write(list(filtered_df.columns))
        
        # ============================================
        # TASK SET 1: DATA EXPLORATION
        # ============================================
        elif task_set == "Task 1: Data Exploration":
            st.header("🔍 Task Set 1: Data Exploration")
            
            # Task 1.1: Display first 5 rows
            st.subheader("Task 1.1: Display First 5 Rows")
            st.info("💡 Hint: Use pd.read_csv() or upload via Streamlit")
            st.dataframe(filtered_df.head(), use_container_width=True)
            
            st.markdown("---")
            
            # Task 1.2: Count missing values
            st.subheader("Task 1.2: Count Missing Values")
            st.info("💡 Hint: Use df.isnull().sum()")
            
            missing_values = filtered_df.isnull().sum()
            missing_df = pd.DataFrame({
                'Column': missing_values.index,
                'Missing Count': missing_values.values,
                'Missing %': (missing_values.values / len(filtered_df) * 100).round(2) if len(filtered_df) > 0 else 0
            })
            st.dataframe(missing_df, use_container_width=True)
            
            st.markdown("---")
            
            # Task 1.3: Identify columns with most missing values
            st.subheader("Task 1.3: Columns with Most Missing Values")
            st.info("💡 Hint: Look for Department, Project, or Owner")
            
            most_missing = missing_df[missing_df['Missing Count'] > 0].nlargest(3, 'Missing Count')
            if not most_missing.empty:
                st.dataframe(most_missing, use_container_width=True)
                st.warning(f"⚠️ Top columns with missing values: {', '.join(most_missing['Column'].tolist())}")
                
                # Visualization
                fig = px.bar(missing_df[missing_df['Missing Count'] > 0], 
                             x='Column', y='Missing Count',
                             title='Missing Values by Column',
                             color='Missing %',
                             color_continuous_scale='Reds')
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.success("✅ No missing values found!")
            
            st.markdown("---")
            
            # Task 1.4: Count tagged vs untagged
            st.subheader("Task 1.4: Count Tagged vs Untagged Resources")
            st.info("💡 Hint: Use df['Tagged'].value_counts()")
            
            tagged_counts = filtered_df['Tagged'].value_counts()
            total_resources = len(filtered_df)
            untagged_count = tagged_counts.get('No', 0)
            tagged_count = tagged_counts.get('Yes', 0)
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Total Resources", total_resources)
                st.metric("Tagged Resources", tagged_count)
                st.metric("Untagged Resources", untagged_count)
            
            with col2:
                # Pie chart
                if len(tagged_counts) > 0:
                    fig = px.pie(tagged_counts.reset_index(), values='count', names='Tagged',
                                title='Tagged vs Untagged Distribution',
                                color='Tagged',
                                color_discrete_map={'Yes': '#28a745', 'No': '#dc3545'})
                    st.plotly_chart(fig, use_container_width=True)
            
            st.markdown("---")
            
            # Task 1.5: Calculate percentage of untagged resources
            st.subheader("Task 1.5: Percentage of Untagged Resources")
            st.info("💡 Hint: Compute (untagged/total)*100")
            
            untagged_pct = (untagged_count / total_resources) * 100 if total_resources > 0 else 0
            
            st.metric("Untagged Percentage", f"{untagged_pct:.2f}%")
            st.info(f"📊 Out of {total_resources} total resources, {untagged_count} are untagged ({untagged_pct:.2f}%)")
        
        # ============================================
        # TASK SET 2: COST VISIBILITY
        # ============================================
        elif task_set == "Task 2: Cost Visibility":
            st.header("💰 Task Set 2: Cost Visibility")
            
            # Task 2.1: Calculate total cost by tagging status
            st.subheader("Task 2.1: Total Cost by Tagging Status")
            st.info("💡 Hint: Group by 'Tagged' and sum 'MonthlyCostUSD'")
            
            cost_by_tagged = filtered_df.groupby('Tagged')['MonthlyCostUSD'].sum()
            total_cost = filtered_df['MonthlyCostUSD'].sum()
            untagged_cost = cost_by_tagged.get('No', 0)
            tagged_cost = cost_by_tagged.get('Yes', 0)
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Cost", f"${total_cost:,.2f}")
            with col2:
                st.metric("Tagged Cost", f"${tagged_cost:,.2f}")
            with col3:
                st.metric("Untagged Cost", f"${untagged_cost:,.2f}")
            
            # Bar chart
            cost_df = pd.DataFrame({
                'Status': ['Tagged', 'Untagged'],
                'Cost': [tagged_cost, untagged_cost]
            })
            fig = px.bar(cost_df, x='Status', y='Cost', 
                        title='Cost by Tagging Status',
                        color='Status',
                        color_discrete_map={'Tagged': '#28a745', 'Untagged': '#dc3545'})
            st.plotly_chart(fig, use_container_width=True)
            
            st.markdown("---")
            
            # Task 2.2: Calculate percentage of untagged cost
            st.subheader("Task 2.2: Percentage of Untagged Cost")
            st.info("💡 Hint: Compute (untagged_cost/total_cost)*100")
            
            untagged_cost_pct = (untagged_cost / total_cost) * 100 if total_cost > 0 else 0
            
            st.metric("Untagged Cost Percentage", f"{untagged_cost_pct:.2f}%")
            st.info(f"📊 ${untagged_cost:,.2f} out of ${total_cost:,.2f} is untagged ({untagged_cost_pct:.2f}%)")
            
            st.markdown("---")
            
            # Task 2.3: Department with most untagged cost
            st.subheader("Task 2.3: Department with Most Untagged Cost")
            st.info("💡 Hint: Filter by Tagged=='No' and group by 'Department'")
            
            if 'Department' in filtered_df.columns:
                dept_cost = filtered_df[filtered_df['Tagged'] == 'No'].groupby('Department')['MonthlyCostUSD'].sum().sort_values(ascending=False)
                
                if not dept_cost.empty:
                    st.dataframe(dept_cost.reset_index().rename(columns={'MonthlyCostUSD': 'Untagged Cost (USD)'}), 
                                 use_container_width=True)
                    st.success(f"🏆 Department with most untagged cost: **{dept_cost.index[0]}** (${dept_cost.iloc[0]:,.2f})")
                    
                    # Bar chart
                    fig = px.bar(dept_cost.reset_index(), x='Department', y='MonthlyCostUSD',
                                 title='Untagged Cost by Department',
                                 color='MonthlyCostUSD',
                                 color_continuous_scale='Reds')
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.success("✅ No untagged costs found!")
            else:
                st.warning("⚠️ 'Department' column not found in dataset")
            
            st.markdown("---")
            
            # Task 2.4: Project with most cost
            st.subheader("Task 2.4: Project Consuming Most Cost")
            st.info("💡 Hint: Use .groupby('Project')['MonthlyCostUSD'].sum()")
            
            if 'Project' in filtered_df.columns:
                project_cost = filtered_df.groupby('Project')['MonthlyCostUSD'].sum().sort_values(ascending=False)
                
                if not project_cost.empty:
                    st.dataframe(project_cost.reset_index().rename(columns={'MonthlyCostUSD': 'Total Cost (USD)'}),
                                 use_container_width=True)
                    st.success(f"🏆 Project consuming most cost: **{project_cost.index[0]}** (${project_cost.iloc[0]:,.2f})")
                    
                    # Bar chart
                    fig = px.bar(project_cost.reset_index(), x='Project', y='MonthlyCostUSD',
                                 title='Total Cost by Project',
                                 color='MonthlyCostUSD',
                                 color_continuous_scale='Blues')
                    st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("⚠️ 'Project' column not found in dataset")
            
            st.markdown("---")
            
            # Task 2.5: Compare Prod vs Dev vs Test
            st.subheader("Task 2.5: Compare Prod vs Dev vs Test Environments")
            st.info("💡 Hint: Group by 'Environment' and 'Tagged'")
            
            if 'Environment' in filtered_df.columns:
                # Grouped analysis
                env_analysis = filtered_df.groupby(['Environment', 'Tagged'])['MonthlyCostUSD'].sum().reset_index()
                
                fig = px.bar(env_analysis, x='Environment', y='MonthlyCostUSD',
                             color='Tagged', barmode='group',
                             title='Cost and Tagging Quality by Environment',
                             labels={'MonthlyCostUSD': 'Monthly Cost (USD)'},
                             color_discrete_map={'Yes': '#28a745', 'No': '#dc3545'})
                st.plotly_chart(fig, use_container_width=True)
                
                # Summary table
                env_summary = filtered_df.groupby('Environment').agg({
                    'MonthlyCostUSD': 'sum',
                    'ResourceID': 'count'
                }).round(2)
                env_summary.columns = ['Total Cost (USD)', 'Resource Count']
                st.dataframe(env_summary, use_container_width=True)
            else:
                st.warning("⚠️ 'Environment' column not found in dataset")
        
        # ============================================
        # TASK SET 3: TAGGING COMPLIANCE
        # ============================================
        elif task_set == "Task 3: Tagging Compliance":
            st.header("✅ Task Set 3: Tagging Compliance")
            
            tag_fields = ['Department', 'Project', 'Environment', 'Owner', 'CostCenter']
            existing_tag_fields = [field for field in tag_fields if field in filtered_df.columns]
            
            # Task 3.1: Tag Completeness Score
            st.subheader("Task 3.1: Create Tag Completeness Score")
            st.info("💡 Hint: Count how many of the tag fields are non-empty")
            
            df_copy = filtered_df.copy()
            df_copy['TagCompletenessScore'] = df_copy[existing_tag_fields].notna().sum(axis=1)
            df_copy['CompletenessPercentage'] = (df_copy['TagCompletenessScore'] / len(existing_tag_fields)) * 100
            
            st.dataframe(df_copy[['ResourceID', 'Service', 'TagCompletenessScore', 
                                  'CompletenessPercentage', 'MonthlyCostUSD']].head(10),
                        use_container_width=True)
            
            st.markdown("---")
            
            # Task 3.2: Resources with lowest completeness
            st.subheader("Task 3.2: Identify Top 5 Resources with Lowest Completeness")
            st.info("💡 Hint: Sort by TagCompletenessScore ascending")
            
            display_columns = ['ResourceID', 'Service'] + existing_tag_fields + ['TagCompletenessScore', 'CompletenessPercentage', 'MonthlyCostUSD']
            
            lowest_completeness = df_copy.nsmallest(5, 'TagCompletenessScore')[
                [col for col in display_columns if col in df_copy.columns]
            ]
            st.dataframe(lowest_completeness, use_container_width=True)
            
            st.markdown("---")
            
            # Task 3.3: Most frequently missing tag fields
            st.subheader("Task 3.3: Most Frequently Missing Tag Fields")
            st.info("💡 Hint: Count missing entries per tag column")
            
            missing_tags = filtered_df[existing_tag_fields].isnull().sum().sort_values(ascending=False)
            missing_tags_df = pd.DataFrame({
                'Tag Field': missing_tags.index,
                'Missing Count': missing_tags.values,
                'Missing %': (missing_tags.values / len(filtered_df) * 100).round(2) if len(filtered_df) > 0 else 0
            })
            
            st.dataframe(missing_tags_df, use_container_width=True)
            
            if missing_tags.sum() > 0:
                fig = px.bar(missing_tags_df, x='Tag Field', y='Missing Count',
                             title='Missing Tag Fields',
                             color='Missing %',
                             color_continuous_scale='Oranges')
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.success("✅ No missing tag fields!")
            
            st.markdown("---")
            
            # Task 3.4: List untagged resources
            st.subheader("Task 3.4: List Untagged Resources and Their Costs")
            st.info("💡 Hint: Filter where Tagged == 'No'")
            
            display_cols = ['ResourceID', 'Service', 'Region'] + existing_tag_fields + ['MonthlyCostUSD']
            
            untagged_resources = filtered_df[filtered_df['Tagged'] == 'No'][
                [col for col in display_cols if col in filtered_df.columns]
            ]
            st.dataframe(untagged_resources, use_container_width=True)
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Total Untagged Resources", len(untagged_resources))
            with col2:
                st.metric("Total Untagged Cost", f"${untagged_resources['MonthlyCostUSD'].sum():,.2f}")
            
            st.markdown("---")
            
            # Task 3.5: Export untagged resources
            st.subheader("Task 3.5: Export Untagged Resources to CSV")
            st.info("💡 Hint: Use df[df['Tagged']=='No'].to_csv('untagged.csv')")
            
            csv_buffer = BytesIO()
            untagged_resources.to_csv(csv_buffer, index=False)
            csv_buffer.seek(0)
            
            st.download_button(
                label="📥 Download Untagged Resources CSV",
                data=csv_buffer,
                file_name="untagged_resources.csv",
                mime="text/csv"
            )
        
        # ============================================
        # TASK SET 4: VISUALIZATION DASHBOARD
        # ============================================
        elif task_set == "Task 4: Visualization Dashboard":
            st.header("📊 Task Set 4: Visualization Dashboard")
            
            # Task 4.1: Pie chart
            st.subheader("Task 4.1: Pie Chart - Tagged vs Untagged")
            st.info("💡 Hint: Use plotly.express.pie")
            
            tagged_counts = filtered_df['Tagged'].value_counts().reset_index()
            tagged_counts.columns = ['Tagged', 'Count']
            
            if len(tagged_counts) > 0:
                fig = px.pie(tagged_counts, values='Count', names='Tagged',
                             title='Resource Tagging Status Distribution',
                             color='Tagged',
                             color_discrete_map={'Yes': '#28a745', 'No': '#dc3545'})
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No data to display")
            
            st.markdown("---")
            
            # Task 4.2: Bar chart by department
            st.subheader("Task 4.2: Bar Chart - Cost per Department by Tagging Status")
            st.info("💡 Hint: Use barmode='group'")
            
            if 'Department' in filtered_df.columns:
                dept_cost_tagged = filtered_df.groupby(['Department', 'Tagged'])['MonthlyCostUSD'].sum().reset_index()
                
                if len(dept_cost_tagged) > 0:
                    fig = px.bar(dept_cost_tagged, x='Department', y='MonthlyCostUSD',
                                 color='Tagged', barmode='group',
                                 title='Cost by Department and Tagging Status',
                                 labels={'MonthlyCostUSD': 'Monthly Cost (USD)'},
                                 color_discrete_map={'Yes': '#28a745', 'No': '#dc3545'})
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No data to display")
            else:
                st.warning("⚠️ 'Department' column not found")
            
            st.markdown("---")
            
            # Task 4.3: Horizontal bar chart
            st.subheader("Task 4.3: Horizontal Bar Chart - Total Cost per Service")
            st.info("💡 Hint: Group by 'Service' and use orientation='h'")
            
            service_cost = filtered_df.groupby('Service')['MonthlyCostUSD'].sum().sort_values().reset_index()
            
            if len(service_cost) > 0:
                fig = px.bar(service_cost, y='Service', x='MonthlyCostUSD',
                             orientation='h',
                             title='Total Cost by Service Type',
                             labels={'MonthlyCostUSD': 'Monthly Cost (USD)'},
                             color='MonthlyCostUSD',
                             color_continuous_scale='Viridis')
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No data to display")
            
            st.markdown("---")
            
            # Task 4.4: Environment cost distribution
            st.subheader("Task 4.4: Cost by Environment (Prod/Dev/Test)")
            st.info("💡 Hint: Pie or bar chart works")
            
            if 'Environment' in filtered_df.columns:
                env_cost = filtered_df.groupby('Environment')['MonthlyCostUSD'].sum().reset_index()
                
                if len(env_cost) > 0:
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        fig = px.pie(env_cost, values='MonthlyCostUSD', names='Environment',
                                     title='Cost Distribution by Environment',
                                     color_discrete_sequence=px.colors.sequential.RdBu)
                        st.plotly_chart(fig, use_container_width=True)
                    
                    with col2:
                        fig = px.bar(env_cost, x='Environment', y='MonthlyCostUSD',
                                     title='Cost by Environment',
                                     color='MonthlyCostUSD',
                                     color_continuous_scale='Blues')
                        st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No data to display")
            else:
                st.warning("⚠️ 'Environment' column not found")
            
            st.markdown("---")
            
            # Task 4.5: Note about filters
            st.subheader("Task 4.5: Interactive Filters")
            st.success("✅ Global filters are available in the sidebar and apply to all visualizations!")
        
        # ============================================
        # TASK SET 5: TAG REMEDIATION WORKFLOW
        # ============================================
        elif task_set == "Task 5: Tag Remediation":
            st.header("🔧 Task Set 5: Tag Remediation Workflow")
            
            # Initialize edited dataframe
            if st.session_state.df_edited is None:
                st.session_state.df_edited = df.copy()
            
            # Task 5.1: Display editable table
            st.subheader("Task 5.1: Display Editable Table for Untagged Resources")
            st.info("💡 Hint: Use st.data_editor")
            
            st.markdown("💡 **Tip:** Double-click on any cell to edit. Fill in missing Department, Project, and Owner fields.")
            
            # Get untagged resources (apply filters to edited dataframe)
            untagged_mask = st.session_state.df_edited['Tagged'] == 'No'
            untagged_df_full = st.session_state.df_edited[untagged_mask].copy()
            
            # Apply same filters as sidebar
            untagged_df = untagged_df_full.copy()
            if selected_service != 'All':
                untagged_df = untagged_df[untagged_df['Service'] == selected_service]
            if selected_region != 'All' and 'Region' in untagged_df.columns:
                untagged_df = untagged_df[untagged_df['Region'] == selected_region]
            if selected_department != 'All' and 'Department' in untagged_df.columns:
                untagged_df = untagged_df[untagged_df['Department'] == selected_department]
            if selected_environment != 'All' and 'Environment' in untagged_df.columns:
                untagged_df = untagged_df[untagged_df['Environment'] == selected_environment]
            
            if len(untagged_df) > 0:
                st.info(f"Found {len(untagged_df)} untagged resources to remediate")
                
                # Determine which columns to make editable
                disabled_columns = ['AccountID', 'ResourceID', 'Service', 'Region', 'MonthlyCostUSD', 'CreatedBy', 'Tagged']
                
                # Display editable table - CAPTURE THE EDITED DATA
                edited_data = st.data_editor(
                    untagged_df,
                    use_container_width=True,
                    num_rows="fixed",
                    disabled=[col for col in disabled_columns if col in untagged_df.columns],
                    key='data_editor'
                )
                
                # Store edited data in session state
                if 'last_edited_data' not in st.session_state:
                    st.session_state.last_edited_data = None
                    
            else:
                st.success("🎉 Great! There are no untagged resources to remediate with the current filters.")
                edited_data = None
            
            st.markdown("---")
            
            # Task 5.2: Simulate remediation
            st.subheader("Task 5.2: Simulate Remediation by Filling Missing Tags")
            st.info("💡 Hint: Apply changes and update Tagged status")
            
            if edited_data is not None and len(edited_data) > 0:
                if st.button("✅ Apply Changes and Update Tagged Status", type="primary"):
                    # Update the main dataframe with edited data
                    changes_made = 0
                    for idx, row in edited_data.iterrows():
                        # Check if all important fields are filled
                        has_dept = pd.notna(row.get('Department', None)) if 'Department' in row else True
                        has_project = pd.notna(row.get('Project', None)) if 'Project' in row else True
                        has_owner = pd.notna(row.get('Owner', None)) if 'Owner' in row else True
                        
                        # Update all fields first
                        for col in edited_data.columns:
                            st.session_state.df_edited.at[idx, col] = row[col]
                        
                        # Then check if should be marked as tagged
                        if has_dept and has_project and has_owner:
                            st.session_state.df_edited.at[idx, 'Tagged'] = 'Yes'
                            changes_made += 1
                    
                    if changes_made > 0:
                        st.success(f"✅ {changes_made} resource(s) updated successfully! Resources with complete tags have been marked as 'Tagged'.")
                    else:
                        st.warning("⚠️ No resources were fully tagged. Make sure to fill Department, Project, AND Owner fields.")
                    
                    # Force reload
                    st.rerun()
            
            st.markdown("---")
            
            # Task 5.3: Download updated dataset
            st.subheader("Task 5.3: Download the Remediated Dataset")
            st.info("💡 Hint: Use st.download_button")
            
            col1, col2 = st.columns(2)
            
            with col1:
                csv_buffer = BytesIO()
                st.session_state.df_edited.to_csv(csv_buffer, index=False)
                csv_buffer.seek(0)
                
                st.download_button(
                    label="📥 Download Remediated Dataset",
                    data=csv_buffer,
                    file_name="cloudmart_remediated.csv",
                    mime="text/csv"
                )
            
            with col2:
                # Original dataset download
                csv_buffer_original = BytesIO()
                st.session_state.original_df.to_csv(csv_buffer_original, index=False)
                csv_buffer_original.seek(0)
                
                st.download_button(
                    label="📥 Download Original Dataset",
                    data=csv_buffer_original,
                    file_name="cloudmart_original.csv",
                    mime="text/csv"
                )
            
            st.markdown("---")
            
            # Task 5.4: Before and after comparison
            st.subheader("Task 5.4: Compare Before and After Remediation")
            st.info("💡 Hint: Recalculate tagging metrics after updates")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("#### 📊 Before Remediation")
                before_tagged = st.session_state.original_df['Tagged'].value_counts()
                before_untagged = before_tagged.get('No', 0)
                before_total = len(st.session_state.original_df)
                before_pct = (before_untagged / before_total) * 100
                before_cost = st.session_state.original_df[st.session_state.original_df['Tagged'] == 'No']['MonthlyCostUSD'].sum()
                
                st.metric("Untagged Resources", f"{before_untagged} ({before_pct:.2f}%)")
                st.metric("Untagged Cost", f"${before_cost:,.2f}")
            
            with col2:
                st.markdown("#### ✅ After Remediation")
                after_tagged = st.session_state.df_edited['Tagged'].value_counts()
                after_untagged = after_tagged.get('No', 0)
                after_total = len(st.session_state.df_edited)
                after_pct = (after_untagged / after_total) * 100
                after_cost = st.session_state.df_edited[st.session_state.df_edited['Tagged'] == 'No']['MonthlyCostUSD'].sum()
                
                improvement = before_untagged - after_untagged
                cost_improvement = before_cost - after_cost
                
                st.metric("Untagged Resources", f"{after_untagged} ({after_pct:.2f}%)", 
                         delta=f"-{improvement}", delta_color="inverse")
                st.metric("Untagged Cost", f"${after_cost:,.2f}",
                         delta=f"-${cost_improvement:,.2f}", delta_color="inverse")
            
            # Visualization comparison
            col1, col2 = st.columns(2)
            
            with col1:
                fig = go.Figure()
                fig.add_trace(go.Bar(name='Before', x=['Untagged Resources'], 
                                     y=[before_untagged], marker_color='#dc3545'))
                fig.add_trace(go.Bar(name='After', x=['Untagged Resources'], 
                                     y=[after_untagged], marker_color='#28a745'))
                fig.update_layout(title='Remediation Impact on Untagged Resources', 
                                 yaxis_title='Count', barmode='group')
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                fig = go.Figure()
                fig.add_trace(go.Bar(name='Before', x=['Untagged Cost'], 
                                     y=[before_cost], marker_color='#dc3545'))
                fig.add_trace(go.Bar(name='After', x=['Untagged Cost'], 
                                     y=[after_cost], marker_color='#28a745'))
                fig.update_layout(title='Remediation Impact on Untagged Cost', 
                                 yaxis_title='Cost (USD)', barmode='group')
                st.plotly_chart(fig, use_container_width=True)
            
            st.markdown("---")
            
                        # Task 5.5: Reflection with Data-Driven Insights
            st.subheader("Task 5.5: Impact Analysis - How Improved Tagging Affects Accountability")
            st.info("💡 Hint: Analyze the data and discuss accountability improvements")
            
            # Calculate key metrics
            before_tagged_count = st.session_state.original_df['Tagged'].value_counts()
            after_tagged_count = st.session_state.df_edited['Tagged'].value_counts()
            
            before_untagged = before_tagged_count.get('No', 0)
            after_untagged = after_tagged_count.get('No', 0)
            remediated_count = before_untagged - after_untagged
            remediation_rate = (remediated_count / before_untagged * 100) if before_untagged > 0 else 0
            
            before_cost = st.session_state.original_df[st.session_state.original_df['Tagged'] == 'No']['MonthlyCostUSD'].sum()
            after_cost = st.session_state.df_edited[st.session_state.df_edited['Tagged'] == 'No']['MonthlyCostUSD'].sum()
            cost_recovered = before_cost - after_cost
            
            # Key Metrics Dashboard
            st.markdown("### 📊 Remediation Impact Summary")
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Resources Remediated", f"{remediated_count}", 
                         delta=f"{remediation_rate:.1f}% of untagged")
            with col2:
                st.metric("Cost Visibility Gained", f"${cost_recovered:,.2f}",
                         delta="Now trackable")
            with col3:
                completion_rate = ((len(st.session_state.df_edited) - after_untagged) / len(st.session_state.df_edited) * 100)
                st.metric("Overall Compliance", f"{completion_rate:.1f}%",
                         delta=f"+{remediation_rate:.1f}%")
            with col4:
                avg_tags_before = st.session_state.original_df[['Department', 'Project', 'Owner']].notna().sum().sum() / (len(st.session_state.original_df) * 3) * 100
                avg_tags_after = st.session_state.df_edited[['Department', 'Project', 'Owner']].notna().sum().sum() / (len(st.session_state.df_edited) * 3) * 100
                st.metric("Tag Completeness", f"{avg_tags_after:.1f}%",
                         delta=f"+{avg_tags_after - avg_tags_before:.1f}%")
            
            st.markdown("---")
            
            # Visualization 1: Tag Completeness Improvement by Field
            st.markdown("### 🎯 Tag Completeness Improvement by Field")
            
            tag_fields = ['Department', 'Project', 'Owner']
            before_completeness = []
            after_completeness = []
            
            for field in tag_fields:
                if field in st.session_state.original_df.columns:
                    before_pct = (st.session_state.original_df[field].notna().sum() / len(st.session_state.original_df)) * 100
                    after_pct = (st.session_state.df_edited[field].notna().sum() / len(st.session_state.df_edited)) * 100
                    before_completeness.append(before_pct)
                    after_completeness.append(after_pct)
            
            completeness_df = pd.DataFrame({
                'Tag Field': tag_fields * 2,
                'Completeness %': before_completeness + after_completeness,
                'Status': ['Before'] * len(tag_fields) + ['After'] * len(tag_fields)
            })
            
            fig = px.bar(completeness_df, x='Tag Field', y='Completeness %',
                        color='Status', barmode='group',
                        title='Tag Field Completeness: Before vs After Remediation',
                        color_discrete_map={'Before': '#dc3545', 'After': '#28a745'},
                        text='Completeness %')
            fig.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
            fig.update_layout(yaxis_range=[0, 110])
            st.plotly_chart(fig, use_container_width=True)
            
            st.markdown("---")
            
            # Visualization 2: Cost Accountability by Department
            st.markdown("### 💰 Cost Accountability Impact by Department")
            
            if 'Department' in st.session_state.df_edited.columns:
                # Calculate before/after costs by department
                before_dept_costs = st.session_state.original_df.groupby('Department')['MonthlyCostUSD'].sum().reset_index()
                before_dept_costs.columns = ['Department', 'Total Cost']
                
                # Calculate untagged costs
                before_untagged_dept = st.session_state.original_df[st.session_state.original_df['Tagged'] == 'No'].groupby('Department')['MonthlyCostUSD'].sum().reset_index()
                before_untagged_dept.columns = ['Department', 'Untagged Cost Before']
                
                after_untagged_dept = st.session_state.df_edited[st.session_state.df_edited['Tagged'] == 'No'].groupby('Department')['MonthlyCostUSD'].sum().reset_index()
                after_untagged_dept.columns = ['Department', 'Untagged Cost After']
                
                # Merge
                dept_comparison = before_dept_costs.merge(before_untagged_dept, on='Department', how='left').merge(after_untagged_dept, on='Department', how='left')
                dept_comparison['Untagged Cost Before'] = dept_comparison['Untagged Cost Before'].fillna(0)
                dept_comparison['Untagged Cost After'] = dept_comparison['Untagged Cost After'].fillna(0)
                dept_comparison['Cost Now Trackable'] = dept_comparison['Untagged Cost Before'] - dept_comparison['Untagged Cost After']
                dept_comparison['Accountability %'] = (dept_comparison['Cost Now Trackable'] / dept_comparison['Total Cost'] * 100).round(1)
                
                # Create visualization
                fig = px.bar(dept_comparison, x='Department', y='Cost Now Trackable',
                            title='Cost Visibility Gained by Department',
                            color='Accountability %',
                            color_continuous_scale='Greens',
                            text='Cost Now Trackable')
                fig.update_traces(texttemplate='$%{text:,.0f}', textposition='outside')
                st.plotly_chart(fig, use_container_width=True)
                
                # Show department accountability table
                dept_display = dept_comparison[['Department', 'Total Cost', 'Cost Now Trackable', 'Accountability %']].sort_values('Cost Now Trackable', ascending=False)
                dept_display['Total Cost'] = dept_display['Total Cost'].apply(lambda x: f'${x:,.2f}')
                dept_display['Cost Now Trackable'] = dept_display['Cost Now Trackable'].apply(lambda x: f'${x:,.2f}')
                dept_display['Accountability %'] = dept_display['Accountability %'].apply(lambda x: f'{x:.1f}%')
                
                st.dataframe(dept_display, use_container_width=True)
            
            st.markdown("---")
            
            # Visualization 3: Tagging Progress Timeline
            st.markdown("### 📈 Tagging Compliance Progress")
            
            col1, col2 = st.columns(2)
            
            with col1:
                # Pie chart comparison
                progress_data = pd.DataFrame({
                    'Status': ['Tagged', 'Untagged', 'Tagged', 'Untagged'],
                    'Count': [
                        before_tagged_count.get('Yes', 0),
                        before_tagged_count.get('No', 0),
                        after_tagged_count.get('Yes', 0),
                        after_tagged_count.get('No', 0)
                    ],
                    'Period': ['Before', 'Before', 'After', 'After']
                })
                
                fig = px.pie(progress_data[progress_data['Period'] == 'Before'], 
                            values='Count', names='Status',
                            title='Before Remediation',
                            color='Status',
                            color_discrete_map={'Tagged': '#28a745', 'Untagged': '#dc3545'},
                            hole=0.4)
                fig.update_traces(textposition='inside', textinfo='percent+label')
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                fig = px.pie(progress_data[progress_data['Period'] == 'After'], 
                            values='Count', names='Status',
                            title='After Remediation',
                            color='Status',
                            color_discrete_map={'Tagged': '#28a745', 'Untagged': '#dc3545'},
                            hole=0.4)
                fig.update_traces(textposition='inside', textinfo='percent+label')
                st.plotly_chart(fig, use_container_width=True)
            
            st.markdown("---")
            
            # Key Insights with Icons
            st.markdown("### 🎯 Key Accountability Improvements")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("""
                #### 📋 **Cost Visibility Benefits**
                
                **Before Remediation:**
                - 🔴 ${:,.2f} in untracked cloud spending
                - 🔴 {:} resources without clear ownership
                - 🔴 No departmental cost attribution
                
                **After Remediation:**
                - 🟢 ${:,.2f} now properly attributed
                - 🟢 {:} resources with clear owners
                - 🟢 Improved budget accountability by {:.1f}%
                """.format(
                    before_cost,
                    before_untagged,
                    cost_recovered,
                    remediated_count,
                    (cost_recovered / before_cost * 100) if before_cost > 0 else 0
                ))
            
            with col2:
                st.markdown("""
                #### 🏢 **Governance Impact**
                
                **Organizational Benefits:**
                - ✅ Clear resource ownership established
                - ✅ Department-level cost tracking enabled
                - ✅ Compliance with tagging policies improved
                - ✅ Better resource lifecycle management
                
                **Financial Control:**
                - ✅ Accurate showback/chargeback reports
                - ✅ Budget variance tracking by department
                - ✅ Cost anomaly detection enabled
                - ✅ Forecasting accuracy improved
                """)
            
            st.markdown("---")
            
            # Actionable Recommendations
            st.markdown("### 🚀 Recommended Next Steps")
            
            # Calculate specific recommendations based on data
            remaining_untagged = after_untagged
            remaining_cost = after_cost
            
            if remaining_untagged > 0:
                st.warning(f"""
                **⚠️ Action Required:** {remaining_untagged} resources (${remaining_cost:,.2f}) still remain untagged.
                
                **Priority Actions:**
                1. 🎯 Focus on high-cost resources first (RDS, EC2 instances)
                2. 📧 Contact resource creators to identify ownership
                3. 🔍 Review resources older than 90 days without tags
                4. 🗑️ Consider decommissioning orphaned resources
                """)
            else:
                st.success("🎉 **Excellent!** All resources are now properly tagged!")
            
            # Best Practices Visualization
            st.markdown("### 📚 Best Practices for Sustained Compliance")
            
            best_practices = pd.DataFrame({
                'Practice': [
                    'Automated Tagging',
                    'Tag Policies',
                    'Regular Audits',
                    'Owner Training',
                    'CI/CD Integration'
                ],
                'Impact': [95, 90, 85, 80, 92],
                'Effort': [60, 40, 30, 20, 70],
                'Category': ['Automation', 'Policy', 'Process', 'People', 'Automation']
            })
            
            fig = px.scatter(best_practices, x='Effort', y='Impact', size='Impact',
                            color='Category', text='Practice',
                            title='Best Practices: Impact vs Implementation Effort',
                            labels={'Impact': 'Effectiveness (%)', 'Effort': 'Implementation Effort (%)'},
                            color_discrete_sequence=px.colors.qualitative.Set2)
            fig.update_traces(textposition='top center')
            fig.update_layout(showlegend=True)
            st.plotly_chart(fig, use_container_width=True)
            
            # ROI Calculation
            st.markdown("### 💵 Estimated ROI of Tag Remediation")
            
            # Calculate potential savings
            monthly_savings = cost_recovered * 0.15  # Assume 15% optimization from visibility
            annual_savings = monthly_savings * 12
            remediation_hours = remediated_count * 0.25  # 15 min per resource
            remediation_cost = remediation_hours * 50  # $50/hour average
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("One-time Cost", f"${remediation_cost:,.0f}",
                         delta="Remediation effort")
            with col2:
                st.metric("Monthly Savings", f"${monthly_savings:,.0f}",
                         delta="15% optimization")
            with col3:
                roi_months = remediation_cost / monthly_savings if monthly_savings > 0 else 0
                st.metric("Break-even Period", f"{roi_months:.1f} months",
                         delta=f"${annual_savings:,.0f}/year")
            
            # ROI visualization
            months = list(range(0, 13))
            cumulative_savings = [monthly_savings * m - remediation_cost for m in months]
            
            roi_df = pd.DataFrame({
                'Month': months,
                'Net Benefit': cumulative_savings
            })
            
            fig = px.line(roi_df, x='Month', y='Net Benefit',
                         title='Cumulative ROI from Tag Remediation',
                         markers=True)
            fig.add_hline(y=0, line_dash="dash", line_color="red", 
                         annotation_text="Break-even")
            fig.update_layout(yaxis_title='Cumulative Net Benefit ($)')
            st.plotly_chart(fig, use_container_width=True)

        
        # Footer
        st.sidebar.markdown("---")
        st.sidebar.info("""
        **CloudMart Cost Governance Dashboard**  
        Week 10 Activity - Cloud Economics  
        Fall 2025
        """)
        
else:
    # Landing page when no file is uploaded
    st.info("👆 Please upload your CloudMart CSV file to begin the analysis")
    
    st.markdown("""
    ### 📋 Lab Objectives
    By the end of this lab, you will be able to:
    - ✅ Understand the structure and importance of resource tagging in cloud environments
    - ✅ Measure tagging compliance and cost visibility
    - ✅ Identify untagged resources and quantify their hidden costs
    - ✅ Visualize cloud costs across departments, services, and environments
    - ✅ Simulate tag remediation and observe its effect on cost reporting
    
    ### 📂 Expected CSV Format
    Your CSV file should contain the following columns:
    - AccountID
    - ResourceID
    - Service
    - Region
    - Department
    - Project
    - Environment
    - Owner
    - CostCenter
    - CreatedBy
    - MonthlyCostUSD
    - Tagged
    """)
